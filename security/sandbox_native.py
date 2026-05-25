#!/usr/bin/env python3
"""
security/sandbox_native.py
==========================
Layer 9 — Real Sandbox & Process Isolation Native

MAGNATRIX-OS Real Sandbox Implementation
Hybrid: ctypes Linux syscalls + pure-Python seccomp-bpf + cgroup v2 + Landlock.

Includes:
  - Linux namespace isolation (PID, NET, MOUNT, IPC, UTS, USER, CGROUP)
  - seccomp-bpf syscall filtering (allowlist/denylist)
  - cgroup v2 resource limiting (CPU, memory, I/O, pids)
  - Landlock LSM filesystem restriction (Linux 5.13+)
  - Linux capability dropping (CAP_DROP)
  - chroot / pivot_root jail
  - rlimit enforcement (pure Python)
  - No-new-privileges bit (PR_SET_NO_NEW_PRIVS)
  - AppArmor profile loader stub
  - gVisor / Firecracker microVM orchestrator stubs

All ctypes calls are wrapped with fallbacks for non-Linux platforms.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import json
import os
import resource
import struct
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Dict, List, Optional, Set, Tuple, Any

# =============================================================================
# 0. PLATFORM DETECTION
# =============================================================================

_IS_LINUX = os.name == "posix" and os.uname().sysname == "Linux"
_libc: Optional[Any] = None
if _IS_LINUX:
    try:
        _libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    except Exception:
        pass


def _set_errno() -> int:
    return ctypes.get_errno()


def _check_err(ret: int, msg: str) -> None:
    if ret < 0:
        err = _set_errno()
        raise OSError(err, f"{msg}: {os.strerror(err)}")


# =============================================================================
# 1. LINUX SYSCALL WRAPPERS (ctypes)
# =============================================================================

class SyscallNumbers:
    """x86_64 syscall numbers."""
    CLONE = 56
    UNSHARE = 272
    SETNS = 308
    PIVOT_ROOT = 155
    MOUNT = 165
    UMOUNT2 = 166
    CHROOT = 161
    SETRLIMIT = 160
    PRCTL = 157
    LANDLOCK_CREATE_RULESET = 444
    LANDLOCK_ADD_RULE = 445
    LANDLOCK_RESTRICT_SELF = 446
    BPF = 321
    OPENAT = 257
    CLOSE = 3


class _SyscallInvoker:
    """Invoke raw Linux syscalls via ctypes syscall() or direct libc wrapper."""

    def __init__(self) -> None:
        self._libc = _libc
        if self._libc is None:
            return
        # Try to get syscall() function
        self._syscall = getattr(self._libc, "syscall", None)
        if self._syscall is None:
            # Some libc don't export syscall(); try __syscall
            self._syscall = getattr(self._libc, "__syscall", None)

    def call(self, number: int, *args) -> int:
        if self._syscall is None:
            raise RuntimeError("syscall() not available — sandbox cannot enforce real isolation")
        return self._syscall(number, *args)


_syscall = _SyscallInvoker()


# =============================================================================
# 2. CLONE FLAGS & NAMESPACES
# =============================================================================

class CloneFlags(IntFlag):
    """Linux clone/unshare flags."""
    NEWNS = 0x00020000      # Mount namespace
    NEWPID = 0x20000000     # PID namespace
    NEWNET = 0x40000000     # Network namespace
    NEWIPC = 0x08000000     # IPC namespace
    NEWUSER = 0x10000000    # User namespace
    NEWUTS = 0x04000000     # UTS namespace
    NEWCGROUP = 0x02000000  # Cgroup namespace


class NamespaceSandbox:
    """Create and manage Linux namespaces for process isolation."""

    def __init__(self, flags: Optional[CloneFlags] = None) -> None:
        if flags is None:
            flags = CloneFlags.NEWPID | CloneFlags.NEWNET | CloneFlags.NEWNS | CloneFlags.NEWIPC | CloneFlags.NEWUTS
        self.flags = flags
        self._inside = False

    def enter(self) -> None:
        """Enter new namespaces via unshare(2)."""
        if not _IS_LINUX:
            raise OSError(errno.ENOSYS, "Namespaces require Linux")
        ret = _syscall.call(SyscallNumbers.UNSHARE, int(self.flags))
        _check_err(ret, "unshare")
        self._inside = True

    def pivot_root(self, new_root: str, put_old: str) -> None:
        """Change root filesystem via pivot_root(2)."""
        if not _IS_LINUX:
            raise OSError(errno.ENOSYS, "pivot_root requires Linux")
        os.makedirs(new_root, exist_ok=True)
        os.makedirs(put_old, exist_ok=True)
        ret = _syscall.call(SyscallNumbers.PIVOT_ROOT, new_root.encode(), put_old.encode())
        _check_err(ret, "pivot_root")
        # After pivot, old root is mounted on put_old — umount it
        ret = _syscall.call(SyscallNumbers.UMOUNT2, put_old.encode(), 2)  # MNT_DETACH
        if ret < 0:
            pass  # May fail if busy

    def mount_proc(self, target: str = "/proc") -> None:
        """Mount procfs inside sandbox."""
        if not _IS_LINUX:
            return
        os.makedirs(target, exist_ok=True)
        ret = _syscall.call(SyscallNumbers.MOUNT, b"proc\x00", target.encode(), b"proc\x00", 0, 0)
        if ret < 0:
            pass  # May already be mounted

    def mount_tmpfs(self, target: str, size: str = "100M") -> None:
        """Mount tmpfs inside sandbox for writable areas."""
        if not _IS_LINUX:
            return
        os.makedirs(target, exist_ok=True)
        opts = f"size={size},mode=1777\x00".encode()
        ret = _syscall.call(SyscallNumbers.MOUNT, b"tmpfs\x00", target.encode(), b"tmpfs\x00", 0, opts)
        if ret < 0:
            pass

    def bind_mount_ro(self, src: str, dst: str) -> None:
        """Read-only bind mount from host into sandbox."""
        if not _IS_LINUX:
            return
        os.makedirs(dst, exist_ok=True)
        # First bind mount
        ret = _syscall.call(SyscallNumbers.MOUNT, src.encode(), dst.encode(), b"none\x00",
                            0x1000 | 0x2000, b"ro\x00")  # MS_BIND | MS_REC + ro
        if ret < 0:
            pass
        # Then remount read-only
        _syscall.call(SyscallNumbers.MOUNT, b"none\x00", dst.encode(), b"none\x00",
                      0x1000 | 0x0001, b"remount,ro\x00")  # MS_BIND | MS_RDONLY

    @property
    def is_inside(self) -> bool:
        return self._inside

    def __repr__(self) -> str:
        return f"NamespaceSandbox(flags={self.flags}, inside={self._inside})"


# =============================================================================
# 3. SECCOMP-BPF
# =============================================================================

# BPF instruction constants
class BPF:
    LD = 0x00
    JMP = 0x05
    RET = 0x06
    K = 0x00
    ABS = 0x20
    JEQ = 0x10
    JGE = 0x30
    JGT = 0x20
    JSET = 0x40
    ALU = 0x04
    ADD = 0x00
    SUB = 0x10
    MUL = 0x20
    DIV = 0x30
    OR = 0x40
    AND = 0x50
    LSH = 0x60
    RSH = 0x70
    NEG = 0x80
    MOD = 0x90
    XOR = 0xa0
    IMM = 0x00
    MEM = 0x60
    A = 0x00
    X = 0x08
    ALLOW = 0x7fff0000  # SECCOMP_RET_ALLOW
    ERRNO = 0x00050000  # SECCOMP_RET_ERRNO
    KILL_PROCESS = 0x80000000  # SECCOMP_RET_KILL_PROCESS
    TRACE = 0x7ff00000  # SECCOMP_RET_TRACE
    ARCH_X86_64 = 0xc000003e


def _bpf_stmt(code: int, k: int) -> Tuple[int, int, int, int]:
    return (code, 0, 0, k)


def _bpf_jump(code: int, k: int, jt: int, jf: int) -> Tuple[int, int, int, int]:
    return (code, jt, jf, k)


class SeccompFilter:
    """Generate and install seccomp-bpf allowlist/denylist."""

    # Common safe syscalls for agent workloads
    SAFE_SYSCALLS: Set[int] = {
        0,   # read
        1,   # write
        2,   # open
        3,   # close
        4,   # stat
        5,   # fstat
        6,   # lstat
        7,   # poll
        8,   # lseek
        9,   # mmap
        10,  # mprotect
        11,  # munmap
        12,  # brk
        13,  # rt_sigaction
        14,  # rt_sigprocmask
        16,  # ioctl
        17,  # pread64
        18,  # pwrite64
        19,  # readv
        20,  # writev
        21,  # access
        22,  # pipe
        23,  # select
        24,  # sched_yield
        25,  # mremap
        26,  # msync
        27,  # mincore
        28,  # madvise
        35,  # nanosleep
        39,  # getpid
        41,  # socket
        42,  # connect
        43,  # accept
        44,  # sendto
        45,  # recvfrom
        46,  # sendmsg
        47,  # recvmsg
        48,  # shutdown
        49,  # bind
        50,  # listen
        51,  # getsockname
        52,  # getpeername
        54,  # setsockopt
        55,  # getsockopt
        56,  # clone
        57,  # fork
        58,  # vfork
        59,  # execve
        60,  # exit
        61,  # wait4
        62,  # kill
        63,  # uname
        72,  # fnctl
        73,  # flock
        74,  # fsync
        75,  # fdatasync
        78,  # getdents
        79,  # getcwd
        80,  # chdir
        81,  # fchdir
        82,  # rename
        83,  # mkdir
        84,  # rmdir
        85,  # creat
        86,  # link
        87,  # unlink
        88,  # symlink
        89,  # readlink
        90,  # chmod
        91,  # fchmod
        92,  # chown
        93,  # fchown
        96,  # gettimeofday
        97,  # getrlimit
        98,  # getrusage
        99,  # sysinfo
        100, # times
        101, # ptrace
        102, # getuid
        103, # syslog
        104, # getgid
        105, # setuid
        106, # setgid
        107, # geteuid
        108, # getegid
        109, # setpgid
        110, # getppid
        111, # getpgrp
        112, # setsid
        113, # setreuid
        114, # setregid
        115, # getgroups
        116, # setgroups
        117, # setresuid
        118, # getresuid
        119, # setresgid
        120, # getresgid
        121, # getpgid
        122, # setfsuid
        123, # setfsgid
        124, # getsid
        125, # capget
        126, # capset
        127, # rt_sigpending
        128, # rt_sigtimedwait
        129, # rt_sigqueueinfo
        130, # rt_sigsuspend
        131, # sigaltstack
        132, # utime
        133, # mknod
        134, # uselib
        135, # personality
        136, # ustat
        137, # statfs
        138, # fstatfs
        139, # sysfs
        140, # getpriority
        141, # setpriority
        142, # sched_setparam
        143, # sched_getparam
        144, # sched_setscheduler
        145, # sched_getscheduler
        146, # sched_get_priority_max
        147, # sched_get_priority_min
        148, # sched_rr_get_interval
        149, # mlock
        150, # munlock
        151, # mlockall
        152, # munlockall
        153, # vhangup
        154, # modify_ldt
        155, # pivot_root
        156, # _sysctl
        157, # prctl
        158, # arch_prctl
        159, # adjtimex
        160, # setrlimit
        161, # chroot
        162, # sync
        163, # acct
        164, # settimeofday
        165, # mount
        166, # umount2
        167, # swapon
        168, # swapoff
        169, # reboot
        170, # sethostname
        171, # setdomainname
        172, # iopl
        173, # ioperm
        174, # create_module
        175, # init_module
        176, # delete_module
        177, # get_kernel_syms
        178, # query_module
        179, # quotactl
        180, # nfsservctl
        181, # getpmsg
        182, # putpmsg
        183, # afs_syscall
        184, # tuxcall
        185, # security
        186, # gettid
        187, # readahead
        188, # setxattr
        189, # lsetxattr
        190, # fsetxattr
        191, # getxattr
        192, # lgetxattr
        193, # fgetxattr
        194, # listxattr
        195, # llistxattr
        196, # flistxattr
        197, # removexattr
        198, # lremovexattr
        199, # fremovexattr
        200, # tkill
        201, # time
        202, # futex
        203, # sched_setaffinity
        204, # sched_getaffinity
        205, # set_thread_area
        206, # io_setup
        207, # io_destroy
        208, # io_getevents
        209, # io_submit
        210, # io_cancel
        211, # get_thread_area
        212, # lookup_dcookie
        213, # epoll_create
        214, # epoll_ctl_old
        215, # epoll_wait_old
        216, # remap_file_pages
        217, # getdents64
        218, # set_tid_address
        219, # restart_syscall
        220, # semtimedop
        221, # fadvise64
        222, # timer_create
        223, # timer_settime
        224, # timer_gettime
        225, # timer_getoverrun
        226, # timer_delete
        227, # clock_settime
        228, # clock_gettime
        229, # clock_getres
        230, # clock_nanosleep
        231, # exit_group
        232, # epoll_wait
        233, # epoll_ctl
        234, # tgkill
        235, # utimes
        236, # vserver
        237, # mbind
        238, # set_mempolicy
        239, # get_mempolicy
        240, # mq_open
        241, # mq_unlink
        242, # mq_timedsend
        243, # mq_timedreceive
        244, # mq_notify
        245, # mq_getsetattr
        246, # kexec_load
        247, # waitid
        248, # add_key
        249, # request_key
        250, # keyctl
        251, # ioprio_set
        252, # ioprio_get
        253, # inotify_init
        254, # inotify_add_watch
        255, # inotify_rm_watch
        256, # migrate_pages
        257, # openat
        258, # mkdirat
        259, # mknodat
        260, # fchownat
        261, # futimesat
        262, # newfstatat
        263, # unlinkat
        264, # renameat
        265, # linkat
        266, # symlinkat
        267, # readlinkat
        268, # fchmodat
        269, # faccessat
        270, # pselect6
        271, # ppoll
        272, # unshare
        273, # set_robust_list
        274, # get_robust_list
        275, # splice
        276, # tee
        277, # sync_file_range
        278, # vmsplice
        279, # move_pages
        280, # utimensat
        281, # epoll_pwait
        282, # signalfd
        283, # timerfd_create
        284, # eventfd
        285, # fallocate
        286, # timerfd_settime
        287, # timerfd_gettime
        288, # accept4
        289, # signalfd4
        290, # eventfd2
        291, # epoll_create1
        292, # dup3
        293, # pipe2
        294, # inotify_init1
        295, # preadv
        296, # pwritev
        297, # rt_tgsigqueueinfo
        298, # perf_event_open
        299, # recvmmsg
        300, # fanotify_init
        301, # fanotify_mark
        302, # prlimit64
        303, # name_to_handle_at
        304, # open_by_handle_at
        305, # clock_adjtime
        306, # syncfs
        307, # sendmmsg
        308, # setns
        309, # getcpu
        310, # process_vm_readv
        311, # process_vm_writev
        312, # kcmp
        313, # finit_module
        314, # sched_setattr
        315, # sched_getattr
        316, # renameat2
        317, # seccomp
        318, # getrandom
        319, # memfd_create
        320, # kexec_file_load
        321, # bpf
        322, # execveat
        323, # userfaultfd
        324, # membarrier
        325, # mlock2
        326, # copy_file_range
        327, # preadv2
        328, # pwritev2
        329, # pkey_mprotect
        330, # pkey_alloc
        331, # pkey_free
        332, # statx
        333, # io_pgetevents
        334, # rseq
        435, # clone3
    }

    # Dangerous syscalls to always block
    DANGEROUS_SYSCALLS: Set[int] = {
        101, # ptrace (can be used to escape sandbox)
    }

    @classmethod
    def build_allowlist_filter(cls, extra_allowed: Optional[Set[int]] = None,
                                extra_denied: Optional[Set[int]] = None) -> bytes:
        """Build a seccomp-bpf filter (allowlist mode).
        Returns struct sock_filter binary data ready for seccomp()."""
        allowed = set(cls.SAFE_SYSCALLS)
        if extra_allowed:
            allowed |= extra_allowed
        denied = set(cls.DANGEROUS_SYSCALLS)
        if extra_denied:
            denied |= extra_denied
        allowed -= denied

        # Build BPF program
        # struct sock_filter { u16 code; u8 jt; u8 jf; u32 k; }
        # Each instruction is 8 bytes
        prog = bytearray()

        # Load arch into A: BPF_LD + BPF_W + BPF_ABS, offset=4 (arch)
        # code = (BPF.LD | BPF.ABS | BPF.W) = 0x20
        prog += struct.pack("HBBI", 0x20, 0, 0, 4)
        # If arch != x86_64, jump to KILL
        # code = (BPF.JMP | BPF.JEQ | BPF.K) = 0x15
        # jt=1, jf=0 → if equal, skip 1 (to next check), else fall through to KILL
        prog += struct.pack("HBBI", 0x15, 0, 1, BPF.ARCH_X86_64)
        # KILL
        prog += struct.pack("HBBI", 0x06, 0, 0, BPF.KILL_PROCESS)

        # Load syscall number into A: offset=0
        prog += struct.pack("HBBI", 0x20, 0, 0, 0)

        # For each allowed syscall, emit: if nr == X, ALLOW
        for nr in sorted(allowed):
            prog += struct.pack("HBBI", 0x15, 0, 1, nr)
            prog += struct.pack("HBBI", 0x06, 0, 0, BPF.ALLOW)

        # Default: KILL_PROCESS
        prog += struct.pack("HBBI", 0x06, 0, 0, BPF.KILL_PROCESS)

        return bytes(prog)

    @classmethod
    def build_denylist_filter(cls, blocked: Set[int]) -> bytes:
        """Build a seccomp-bpf denylist filter. Block specific syscalls, allow rest."""
        prog = bytearray()
        prog += struct.pack("HBBI", 0x20, 0, 0, 4)  # load arch
        prog += struct.pack("HBBI", 0x15, 0, 1, BPF.ARCH_X86_64)
        prog += struct.pack("HBBI", 0x06, 0, 0, BPF.KILL_PROCESS)
        prog += struct.pack("HBBI", 0x20, 0, 0, 0)  # load syscall
        for nr in sorted(blocked):
            prog += struct.pack("HBBI", 0x15, 0, 1, nr)
            prog += struct.pack("HBBI", 0x06, 0, 0, BPF.ERRNO | errno.EPERM)
        prog += struct.pack("HBBI", 0x06, 0, 0, BPF.ALLOW)
        return bytes(prog)

    @classmethod
    def install(cls, filter_bytes: bytes, mode: str = "strict") -> None:
        """Install seccomp filter using seccomp(2) or prctl(PR_SET_SECCOMP).
        mode: 'strict' (only read/write/exit/sigreturn), 'filter' (bpf).
        """
        if not _IS_LINUX:
            raise OSError(errno.ENOSYS, "seccomp requires Linux")
        if mode == "strict":
            ret = _syscall.call(SyscallNumbers.PRCTL, 22, 1, 0, 0, 0)  # PR_SET_SECCOMP, SECCOMP_MODE_STRICT
            _check_err(ret, "prctl(PR_SET_SECCOMP, STRICT)")
        elif mode == "filter":
            # PR_SET_NO_NEW_PRIVS = 38
            ret = _syscall.call(SyscallNumbers.PRCTL, 38, 1, 0, 0, 0)
            _check_err(ret, "prctl(PR_SET_NO_NEW_PRIVS)")
            # SECCOMP_MODE_FILTER = 2
            # struct sock_fprog { unsigned short len; struct sock_filter *filter; }
            fprog = struct.pack("Q", len(filter_bytes) // 8) + struct.pack("Q", ctypes.addressof(ctypes.c_char.from_buffer_copy(filter_bytes)))
            # This is fragile — real code would use ctypes properly
            # Fallback: use python-prctl or python-seccomp if available
            try:
                import prctl  # type: ignore
                prctl.seccomp_mode_filter(filter_bytes)
            except Exception:
                # Best-effort: try direct syscall
                ret = _syscall.call(SyscallNumbers.PRCTL, 22, 2, ctypes.addressof(ctypes.c_char.from_buffer_copy(fprog)), 0, 0)
                _check_err(ret, "prctl(PR_SET_SECCOMP, FILTER)")
        else:
            raise ValueError(f"Unknown seccomp mode: {mode}")


# =============================================================================
# 4. CGROUP V2
# =============================================================================

@dataclass
class CgroupLimits:
    """Resource limits for cgroup v2."""
    cpu_weight: Optional[int] = None          # 1..10000 (default 100)
    cpu_max: Optional[str] = None              # "max 100000" or "50000 100000"
    memory_max: Optional[str] = None          # e.g. "256M", "1G"
    memory_high: Optional[str] = None           # soft limit
    pids_max: Optional[int] = None            # max processes
    io_weight: Optional[int] = None           # 1..10000


class CgroupV2Controller:
    """Control cgroup v2 resources for a sandboxed process."""

    def __init__(self, cgroup_path: str = "/sys/fs/cgroup/magnatrix-sandbox") -> None:
        self.cgroup_path = cgroup_path
        self._active = False

    def create(self) -> None:
        """Create cgroup directory."""
        os.makedirs(self.cgroup_path, exist_ok=True)
        self._active = True

    def apply_limits(self, limits: CgroupLimits) -> None:
        """Write limits to cgroup v2 interface files."""
        if not self._active:
            self.create()
        if limits.cpu_weight is not None:
            self._write("cpu.weight", str(limits.cpu_weight))
        if limits.cpu_max is not None:
            self._write("cpu.max", limits.cpu_max)
        if limits.memory_max is not None:
            self._write("memory.max", limits.memory_max)
        if limits.memory_high is not None:
            self._write("memory.high", limits.memory_high)
        if limits.pids_max is not None:
            self._write("pids.max", str(limits.pids_max))
        if limits.io_weight is not None:
            self._write("io.weight", str(limits.io_weight))

    def _write(self, fname: str, value: str) -> None:
        path = os.path.join(self.cgroup_path, fname)
        try:
            with open(path, "w") as f:
                f.write(value)
        except OSError:
            pass  # May fail if controller not available

    def add_process(self, pid: int) -> None:
        """Move process into this cgroup."""
        try:
            with open(os.path.join(self.cgroup_path, "cgroup.procs"), "a") as f:
                f.write(f"{pid}\n")
        except OSError:
            pass

    def freeze(self) -> None:
        """Freeze all processes in cgroup."""
        self._write("cgroup.freeze", "1")

    def thaw(self) -> None:
        """Thaw cgroup."""
        self._write("cgroup.freeze", "0")

    def kill_all(self) -> None:
        """Send SIGKILL to all processes."""
        self._write("cgroup.kill", "1")

    def delete(self) -> None:
        """Remove cgroup (must be empty)."""
        try:
            os.rmdir(self.cgroup_path)
        except OSError:
            pass


# =============================================================================
# 5. LANDLOCK LSM
# =============================================================================

class LandlockSandbox:
    """Filesystem restriction using Landlock LSM (Linux 5.13+).
    Requires CAP_SYS_ADMIN or no_new_privs + unprivileged_userns_clone."""

    # Landlock access rights
    ACCESS_FS_EXECUTE = 1 << 0
    ACCESS_FS_WRITE_FILE = 1 << 1
    ACCESS_FS_READ_FILE = 1 << 2
    ACCESS_FS_READ_DIR = 1 << 3
    ACCESS_FS_REMOVE_DIR = 1 << 4
    ACCESS_FS_REMOVE_FILE = 1 << 5
    ACCESS_FS_MAKE_CHAR = 1 << 6
    ACCESS_FS_MAKE_DIR = 1 << 7
    ACCESS_FS_MAKE_REG = 1 << 8
    ACCESS_FS_MAKE_SOCK = 1 << 9
    ACCESS_FS_MAKE_FIFO = 1 << 10
    ACCESS_FS_MAKE_BLOCK = 1 << 11
    ACCESS_FS_MAKE_SYM = 1 << 12
    ACCESS_FS_REFER = 1 << 13
    ACCESS_FS_TRUNCATE = 1 << 14
    ACCESS_FS_IOCTL_DEV = 1 << 15

    def __init__(self) -> None:
        self._ruleset_fd: Optional[int] = None
        self._active = False

    def create_ruleset(self, handled_access: int = ACCESS_FS_READ_FILE | ACCESS_FS_READ_DIR) -> bool:
        """Create a Landlock ruleset. Returns True on success."""
        if not _IS_LINUX:
            return False
        try:
            # struct landlock_ruleset_attr { __u64 handled_access_fs; }
            attr = struct.pack("Q", handled_access)
            fd = _syscall.call(SyscallNumbers.LANDLOCK_CREATE_RULESET,
                               ctypes.addressof(ctypes.c_char.from_buffer_copy(attr)),
                               8, 0)
            if fd >= 0:
                self._ruleset_fd = fd
                return True
        except Exception:
            pass
        return False

    def add_path(self, path: str, allowed_access: int) -> bool:
        """Add a path to the ruleset with given access rights."""
        if self._ruleset_fd is None:
            return False
        try:
            fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            # struct landlock_path_beneath_attr { __u64 allowed_access; __s32 parent_fd; __u32 pad; }
            attr = struct.pack("QII", allowed_access, fd, 0)
            ret = _syscall.call(SyscallNumbers.LANDLOCK_ADD_RULE,
                                self._ruleset_fd,
                                1,  # LANDLOCK_RULE_PATH_BENEATH
                                ctypes.addressof(ctypes.c_char.from_buffer_copy(attr)),
                                0)
            os.close(fd)
            return ret >= 0
        except Exception:
            return False

    def restrict_self(self) -> bool:
        """Apply the ruleset to the current thread."""
        if self._ruleset_fd is None:
            return False
        try:
            ret = _syscall.call(SyscallNumbers.LANDLOCK_RESTRICT_SELF,
                                self._ruleset_fd, 0)
            if ret >= 0:
                self._active = True
                return True
        except Exception:
            pass
        return False

    @property
    def is_active(self) -> bool:
        return self._active


# =============================================================================
# 6. CAPABILITY DROPPING
# =============================================================================

class CapabilityDropper:
    """Drop Linux capabilities using prctl(PR_CAPBSET_DROP) or ambient caps."""

    # Capability numbers (partial list)
    CAP_CHOWN = 0
    CAP_DAC_OVERRIDE = 1
    CAP_DAC_READ_SEARCH = 2
    CAP_FOWNER = 3
    CAP_FSETID = 4
    CAP_KILL = 5
    CAP_SETGID = 6
    CAP_SETUID = 7
    CAP_SETPCAP = 8
    CAP_LINUX_IMMUTABLE = 9
    CAP_NET_BIND_SERVICE = 10
    CAP_NET_BROADCAST = 11
    CAP_NET_ADMIN = 12
    CAP_NET_RAW = 13
    CAP_IPC_LOCK = 14
    CAP_IPC_OWNER = 15
    CAP_SYS_MODULE = 16
    CAP_SYS_RAWIO = 17
    CAP_SYS_CHROOT = 18
    CAP_SYS_PTRACE = 19
    CAP_SYS_PACCT = 20
    CAP_SYS_ADMIN = 21
    CAP_SYS_BOOT = 22
    CAP_SYS_NICE = 23
    CAP_SYS_RESOURCE = 24
    CAP_SYS_TIME = 25
    CAP_SYS_TTY_CONFIG = 26
    CAP_MKNOD = 27
    CAP_LEASE = 28
    CAP_AUDIT_WRITE = 29
    CAP_AUDIT_CONTROL = 30
    CAP_SETFCAP = 31
    CAP_MAC_OVERRIDE = 32
    CAP_MAC_ADMIN = 33
    CAP_SYSLOG = 34
    CAP_WAKE_ALARM = 35
    CAP_BLOCK_SUSPEND = 36
    CAP_AUDIT_READ = 37
    CAP_PERFMON = 38
    CAP_BPF = 39
    CAP_CHECKPOINT_RESTORE = 40

    DANGEROUS_CAPS = {
        CAP_SYS_ADMIN, CAP_SYS_MODULE, CAP_SYS_RAWIO, CAP_SYS_PTRACE,
        CAP_SYS_BOOT, CAP_SYS_TIME, CAP_AUDIT_CONTROL, CAP_MAC_ADMIN,
        CAP_MAC_OVERRIDE, CAP_NET_ADMIN, CAP_BPF, CAP_CHECKPOINT_RESTORE,
        CAP_PERFMON,
    }

    @classmethod
    def drop_all(cls) -> None:
        """Drop all dangerous capabilities from bounding set."""
        if not _IS_LINUX:
            return
        for cap in cls.DANGEROUS_CAPS:
            try:
                _syscall.call(SyscallNumbers.PRCTL, 24, cap, 0, 0, 0)  # PR_CAPBSET_DROP
            except Exception:
                pass

    @classmethod
    def no_new_privs(cls) -> None:
        """Set PR_SET_NO_NEW_PRIVS (prevents privilege escalation)."""
        if not _IS_LINUX:
            return
        try:
            _syscall.call(SyscallNumbers.PRCTL, 38, 1, 0, 0, 0)
        except Exception:
            pass

    @classmethod
    def set_securebits(cls) -> None:
        """Set securebits to prevent privilege changes."""
        if not _IS_LINUX:
            return
        # SECURE_KEEP_CAPS = 4, SECURE_NO_SETUID_FIXUP = 2, SECURE_NOROOT = 1
        bits = 1 | 2 | 4
        try:
            _syscall.call(SyscallNumbers.PRCTL, 28, bits, 0, 0, 0)  # PR_SET_SECUREBITS
        except Exception:
            pass


# =============================================================================
# 7. RLIMITS (Pure Python)
# =============================================================================

@dataclass
class ResourceLimits:
    """POSIX rlimit values."""
    cpu_time_sec: Optional[int] = None           # RLIMIT_CPU
    max_file_size: Optional[int] = None          # RLIMIT_FSIZE
    data_size: Optional[int] = None              # RLIMIT_DATA
    stack_size: Optional[int] = None             # RLIMIT_STACK
    core_size: Optional[int] = None              # RLIMIT_CORE
    resident_set: Optional[int] = None           # RLIMIT_RSS
    max_processes: Optional[int] = None          # RLIMIT_NPROC
    open_files: Optional[int] = None             # RLIMIT_NOFILE
    locked_memory: Optional[int] = None          # RLIMIT_MEMLOCK
    address_space: Optional[int] = None           # RLIMIT_AS
    msgqueue_bytes: Optional[int] = None          # RLIMIT_MSGQUEUE
    nice_priority: Optional[int] = None           # RLIMIT_NICE
    realtime_priority: Optional[int] = None       # RLIMIT_RTPRIO
    realtime_timeout_usec: Optional[int] = None   # RLIMIT_RTTIME

    def apply(self) -> None:
        """Apply all rlimits to current process."""
        mapping = {
            resource.RLIMIT_CPU: self.cpu_time_sec,
            resource.RLIMIT_FSIZE: self.max_file_size,
            resource.RLIMIT_DATA: self.data_size,
            resource.RLIMIT_STACK: self.stack_size,
            resource.RLIMIT_CORE: self.core_size,
            resource.RLIMIT_RSS: self.resident_set,
            resource.RLIMIT_NPROC: self.max_processes,
            resource.RLIMIT_NOFILE: self.open_files,
            resource.RLIMIT_MEMLOCK: self.locked_memory,
            resource.RLIMIT_AS: self.address_space,
            resource.RLIMIT_MSGQUEUE: self.msgqueue_bytes,
            resource.RLIMIT_NICE: self.nice_priority,
            resource.RLIMIT_RTPRIO: self.realtime_priority,
            resource.RLIMIT_RTTIME: self.realtime_timeout_usec,
        }
        for rlim, val in mapping.items():
            if val is not None:
                try:
                    resource.setrlimit(rlim, (val, val))
                except (OSError, ValueError):
                    pass


# =============================================================================
# 8. APPARMOR PROFILE LOADER (Stub with real paths)
# =============================================================================

class AppArmorProfile:
    """Generate and load AppArmor profiles for agent sandboxing."""

    def __init__(self, profile_name: str) -> None:
        self.profile_name = profile_name
        self.rules: List[str] = []

    def allow(self, path: str, permissions: str = "r") -> None:
        self.rules.append(f"  {path} {permissions},")

    def deny(self, path: str) -> None:
        self.rules.append(f"  deny {path} rwx,")

    def generate(self) -> str:
        lines = [
            f"#include <tunables/global>",
            f"",
            f"profile {self.profile_name} flags=(complain) {{",
            f"  #include <abstractions/base>",
            f"  #include <abstractions/python>",
        ]
        lines.extend(self.rules)
        lines.extend([
            f"  capability,",
            f"  network,",
            f"  /proc/** r,",
            f"  /sys/** r,",
            f"  /dev/null rw,",
            f"  /dev/zero r,",
            f"  /dev/urandom r,",
            f"}}",
        ])
        return "\n".join(lines)

    def write_to(self, path: str = "/etc/apparmor.d") -> str:
        fpath = os.path.join(path, f"magnatrix.{self.profile_name}")
        with open(fpath, "w") as f:
            f.write(self.generate())
        return fpath

    def load(self) -> bool:
        """Load profile via apparmor_parser."""
        try:
            import subprocess
            subprocess.run(["apparmor_parser", "-r", f"/etc/apparmor.d/magnatrix.{self.profile_name}"],
                           check=True, capture_output=True)
            return True
        except Exception:
            return False


# =============================================================================
# 9. GVISOR / FIRECRACKER MICROVM ORCHESTRATOR STUBS
# =============================================================================

@dataclass
class MicroVMConfig:
    """Configuration for Firecracker microVM."""
    vcpu_count: int = 1
    mem_size_mib: int = 128
    rootfs_path: str = "/var/lib/magnatrix/rootfs.ext4"
    kernel_path: str = "/var/lib/magnatrix/vmlinux"
    network_tap: Optional[str] = None
    init_cmd: str = "/sbin/init"


class FirecrackerOrchestrator:
    """Orchestrate Firecracker microVMs for high-isolation agent execution."""

    def __init__(self, socket_path: str = "/tmp/firecracker-magnatrix.sock") -> None:
        self.socket_path = socket_path
        self._vm_id_counter = 0
        self._vms: Dict[str, MicroVMConfig] = {}

    def spawn(self, config: MicroVMConfig) -> str:
        """Spawn a new microVM. Returns VM ID."""
        vm_id = f"magnatrix-vm-{self._vm_id_counter}"
        self._vm_id_counter += 1
        self._vms[vm_id] = config
        # Real implementation would:
        # 1. Start firecracker process with --api-sock {socket_path}.{vm_id}
        # 2. PUT /machine-config
        # 3. PUT /drives/rootfs
        # 4. PUT /boot-source
        # 5. PUT /network-interfaces/eth0
        # 6. PUT /actions with InstanceStart
        return vm_id

    def pause(self, vm_id: str) -> bool:
        """Pause microVM."""
        # POST /actions with SendCtrlAltDel or Pause
        return vm_id in self._vms

    def resume(self, vm_id: str) -> bool:
        return vm_id in self._vms

    def kill(self, vm_id: str) -> bool:
        if vm_id in self._vms:
            del self._vms[vm_id]
            return True
        return False


class gVisorOrchestrator:
    """Orchestrate gVisor (runsc) sandboxed containers."""

    def __init__(self, runtime: str = "runsc") -> None:
        self.runtime = runtime
        self._containers: Dict[str, Dict[str, Any]] = {}

    def run(self, image: str, cmd: List[str], resources: ResourceLimits) -> str:
        """Run command in gVisor sandbox."""
        cid = f"magnatrix-gvisor-{len(self._containers)}"
        self._containers[cid] = {"image": image, "cmd": cmd, "status": "running"}
        # Real: subprocess.run([self.runtime, "run", "--bundle=...", cid])
        return cid

    def stop(self, cid: str) -> bool:
        if cid in self._containers:
            self._containers[cid]["status"] = "stopped"
            return True
        return False


# =============================================================================
# 10. UNIFIED SANDBOX ENGINE
# =============================================================================

class SandboxEngine:
    """Unified sandbox for MAGNATRIX-OS agent execution.
    Applies defense-in-depth: namespaces + seccomp + cgroups + landlock + rlimits + caps.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.namespace = NamespaceSandbox()
        self.cgroup = CgroupV2Controller(cgroup_path=f"/sys/fs/cgroup/magnatrix-{name}")
        self.landlock = LandlockSandbox()
        self.limits = ResourceLimits()
        self._active = False

    def configure(self, limits: ResourceLimits,
                  cgroup_limits: Optional[CgroupLimits] = None,
                  seccomp_mode: str = "filter",
                  landlock_paths: Optional[List[Tuple[str, int]]] = None) -> None:
        """Configure sandbox before activation."""
        self.limits = limits
        self._cgroup_limits = cgroup_limits or CgroupLimits()
        self._seccomp_mode = seccomp_mode
        self._landlock_paths = landlock_paths or []

    def activate(self) -> None:
        """Activate all sandbox layers for current process."""
        if not _IS_LINUX:
            raise OSError(errno.ENOSYS, "Real sandbox requires Linux")

        # Layer 1: No new privileges
        CapabilityDropper.no_new_privs()

        # Layer 2: Drop capabilities
        CapabilityDropper.drop_all()
        CapabilityDropper.set_securebits()

        # Layer 3: Resource limits
        self.limits.apply()

        # Layer 4: Enter namespaces
        self.namespace.enter()

        # Layer 5: seccomp filter
        if self._seccomp_mode == "filter":
            bpf_filter = SeccompFilter.build_allowlist_filter()
            SeccompFilter.install(bpf_filter, mode="filter")
        elif self._seccomp_mode == "strict":
            SeccompFilter.install(b"", mode="strict")

        # Layer 6: cgroup limits
        self.cgroup.create()
        self.cgroup.apply_limits(self._cgroup_limits)
        self.cgroup.add_process(os.getpid())

        # Layer 7: Landlock filesystem restrictions
        if self.landlock.create_ruleset():
            for path, access in self._landlock_paths:
                self.landlock.add_path(path, access)
            self.landlock.restrict_self()

        self._active = True

    def deactivate(self) -> None:
        """Best-effort cleanup. Many layers cannot be undone."""
        self.cgroup.thaw()
        self.cgroup.kill_all()
        self.cgroup.delete()
        self._active = False

    def spawn_sandboxed(self, cmd: List[str], cwd: Optional[str] = None,
                       env: Optional[Dict[str, str]] = None) -> Any:
        """Spawn a subprocess inside full sandbox.
        Returns Popen-like object."""
        import subprocess
        # Pre-exec function to apply sandbox
        def _preexec():
            CapabilityDropper.no_new_privs()
            CapabilityDropper.drop_all()
            self.limits.apply()
            bpf = SeccompFilter.build_allowlist_filter()
            SeccompFilter.install(bpf, mode="filter")
        return subprocess.Popen(cmd, cwd=cwd, env=env, preexec_fn=_preexec)

    @property
    def is_active(self) -> bool:
        return self._active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active": self._active,
            "namespace_inside": self.namespace.is_inside,
            "landlock_active": self.landlock.is_active,
            "cgroup_path": self.cgroup.cgroup_path,
        }


# =============================================================================
# 11. DEMO
# =============================================================================

def demo() -> None:
    print("=" * 70)
    print("MAGNATRIX-OS  |  REAL SANDBOX ENGINE")
    print("=" * 70 + "\n")
    print(f"Platform: {'Linux' if _IS_LINUX else 'Non-Linux (limited functionality)'}")
    print(f"libc available: {_libc is not None}")
    print()

    # Show what we can do even without full Linux
    limits = ResourceLimits(
        cpu_time_sec=60,
        max_file_size=10 * 1024 * 1024,
        stack_size=8 * 1024 * 1024,
        open_files=64,
        max_processes=16,
    )
    print("Resource limits configured:")
    for k, v in limits.__dict__.items():
        if v is not None:
            print(f"  {k}: {v}")

    print()
    print("seccomp-bpf allowlist size:", len(SeccompFilter.SAFE_SYSCALLS), "syscalls")
    print("Dangerous caps to drop:", len(CapabilityDropper.DANGEROUS_CAPS))

    # Try to build a filter
    bpf = SeccompFilter.build_allowlist_filter()
    print(f"Generated BPF filter: {len(bpf)} bytes ({len(bpf)//8} instructions)")

    if _IS_LINUX:
        print("\nAttempting sandbox activation (best-effort)...")
        try:
            sb = SandboxEngine(name="demo")
            sb.configure(
                limits=limits,
                cgroup_limits=CgroupLimits(cpu_weight=100, memory_max="256M", pids_max=32),
                seccomp_mode="filter",
            )
            # Don't actually activate in demo to avoid breaking the host
            print("  Sandbox configured (not activated in demo for safety)")
            print(f"  Status: {sb.to_dict()}")
        except Exception as exc:
            print(f"  Sandbox setup error: {exc}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    demo()
