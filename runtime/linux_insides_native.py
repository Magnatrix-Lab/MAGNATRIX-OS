#!/usr/bin/env python3
"""
linux_insides_native.py
Educational simulation of Linux Kernel Internals in pure Python.
Zero external dependencies. ~1000 lines.
Topics: Process Scheduler, Memory Management, VFS, Networking, Syscalls,
        Interrupts, Kernel Modules, Boot Process.
"""

from __future__ import annotations
import time
import enum
from typing import Any, Optional, Dict, List, Callable, Tuple
from collections import deque

# ============================================================================
# 1. BASE LAYER — Kernel Data Structures & Core Algorithms
# ============================================================================

# --- jiffies: global kernel timer tick counter ---
JIFFIES = 0

def printk(msg: str) -> None:
    """Simulates kernel printk."""
    print(f"[K] {msg}")

class atomic_t:
    """Simulated atomic integer (no real SMP atomicity in pure Python)."""
    def __init__(self, val: int = 0):
        self._val = val
    def inc(self):
        self._val += 1
    def dec(self):
        self._val -= 1
    def read(self) -> int:
        return self._val

# --- Core kernel structs (simplified analogues) ---

class page:
    """Represents a physical page frame."""
    def __init__(self, pfn: int):
        self.pfn = pfn
        self.refcount = atomic_t(0)
        self.flags = 0
        self.mapping: Optional[Any] = None
        self.index = 0
    def __repr__(self):
        return f"page(pfn={self.pfn},ref={self._val})"

class vm_area_struct:
    """Virtual Memory Area — contiguous user-space virtual region."""
    def __init__(self, vm_start: int, vm_end: int, flags: int = 0):
        self.vm_start = vm_start
        self.vm_end = vm_end
        self.vm_flags = flags
        self.vm_mm: Optional[mm_struct] = None
        self.vm_next: Optional[vm_area_struct] = None
    def __repr__(self):
        return f"VMA(0x{self.vm_start:x}-0x{self.vm_end:x})"

class mm_struct:
    """Memory descriptor per process."""
    def __init__(self):
        self.pgd: Optional[Any] = None          # page global directory (simulated)
        self.mmap: Optional[vm_area_struct] = None
        self.mm_users = atomic_t(1)
        self.total_vm = 0
        self.locked_vm = 0
    def __repr__(self):
        return f"mm_struct(mmap={self.mmap is not None})"

class inode:
    """VFS inode — filesystem metadata object."""
    def __init__(self, i_ino: int):
        self.i_ino = i_ino
        self.i_mode = 0o644
        self.i_size = 0
        self.i_count = atomic_t(1)
        self.i_sb: Optional[super_block] = None
        self.i_op = "generic_inode_ops"
    def __repr__(self):
        return f"inode({self.i_ino})"

class dentry:
    """VFS dentry — directory cache entry."""
    def __init__(self, d_name: str, d_parent: Optional[dentry] = None):
        self.d_name = d_name
        self.d_parent = d_parent
        self.d_inode: Optional[inode] = None
        self.d_subdirs: Dict[str, dentry] = {}
        self.d_count = atomic_t(1)
    def __repr__(self):
        return f"dentry({self.d_name})"

class super_block:
    """VFS superblock — mounted filesystem instance."""
    def __init__(self, s_id: str, s_type: str):
        self.s_id = s_id
        self.s_type = s_type
        self.s_root: Optional[dentry] = None
        self.s_inodes: Dict[int, inode] = {}
    def __repr__(self):
        return f"super_block({self.s_id},{self.s_type})"

class sk_buff:
    """Socket buffer — network packet descriptor."""
    def __init__(self, data: bytes):
        self.data = data
        self.len = len(data)
        self.next: Optional[sk_buff] = None
        self.prev: Optional[sk_buff] = None
        self.saddr = "0.0.0.0"
        self.daddr = "0.0.0.0"
        self.sport = 0
        self.dport = 0
    def __repr__(self):
        return f"skb(len={self.len})"

class task_struct:
    """Process/Task descriptor — the central Linux task representation."""
    def __init__(self, pid: int, comm: str = ""):
        self.pid = pid
        self.comm = comm
        self.state = 0          # TASK_RUNNING etc.
        self.mm: Optional[mm_struct] = None
        self.vruntime = 0
        self.prio = 120         # nice 0 -> prio 120
        self.parent: Optional[task_struct] = None
        self.children: List[task_struct] = []
        self.stack = deque(maxlen=16)  # simulated kernel stack trace
    def __repr__(self):
        return f"task(pid={self.pid},{self.comm},vr={self.vruntime})"

# --- Core algorithms from scratch ---

class LinkedList:
    """Simple doubly linked list for kernel-style list simulation."""
    class Node:
        def __init__(self, val: Any):
            self.val = val
            self.prev: Optional[LinkedList.Node] = None
            self.next: Optional[LinkedList.Node] = None
    def __init__(self):
        self.head: Optional[LinkedList.Node] = None
        self.tail: Optional[LinkedList.Node] = None
        self.size = 0
    def append(self, val: Any):
        n = LinkedList.Node(val)
        if not self.head:
            self.head = self.tail = n
        else:
            n.prev = self.tail
            self.tail.next = n
            self.tail = n
        self.size += 1
    def pop_head(self) -> Any:
        if not self.head:
            return None
        val = self.head.val
        self.head = self.head.next
        if self.head:
            self.head.prev = None
        else:
            self.tail = None
        self.size -= 1
        return val
    def __iter__(self):
        cur = self.head
        while cur:
            yield cur.val
            cur = cur.next

class RBTree:
    """Simplified Red-Black Tree for CFS vruntime ordering.
    Not a full balanced-tree implementation; serves as an ordered container.
    """
    class Node:
        def __init__(self, key: int, task: task_struct):
            self.key = key
            self.task = task
            self.left: Optional[RBTree.Node] = None
            self.right: Optional[RBTree.Node] = None
    def __init__(self):
        self.root: Optional[RBTree.Node] = None
        self._count = 0
    def insert(self, key: int, task: task_struct):
        if not self.root:
            self.root = RBTree.Node(key, task)
            self._count += 1
            return
        def _insert(node: RBTree.Node):
            if key < node.key:
                if node.left:
                    _insert(node.left)
                else:
                    node.left = RBTree.Node(key, task)
            else:
                if node.right:
                    _insert(node.right)
                else:
                    node.right = RBTree.Node(key, task)
        _insert(self.root)
        self._count += 1
    def find_min(self) -> Optional[Tuple[int, task_struct]]:
        node = self.root
        if not node:
            return None
        while node.left:
            node = node.left
        return (node.key, node.task)
    def remove_min(self) -> Optional[Tuple[int, task_struct]]:
        # naive removal of leftmost node
        if not self.root:
            return None
        parent = None
        node = self.root
        while node.left:
            parent = node
            node = node.left
        if parent:
            parent.left = node.right
        else:
            self.root = node.right
        self._count -= 1
        return (node.key, node.task)
    def __len__(self):
        return self._count

class HashTable:
    """Simple chained hash table for inode/dentry caches."""
    def __init__(self, buckets: int = 64):
        self.buckets = [[] for _ in range(buckets)]
        self._size = 0
    def _idx(self, key: Any) -> int:
        return hash(key) % len(self.buckets)
    def put(self, key: Any, val: Any):
        i = self._idx(key)
        for entry in self.buckets[i]:
            if entry[0] == key:
                entry[1] = val
                return
        self.buckets[i].append([key, val])
        self._size += 1
    def get(self, key: Any) -> Any:
        i = self._idx(key)
        for entry in self.buckets[i]:
            if entry[0] == key:
                return entry[1]
        return None
    def remove(self, key: Any) -> bool:
        i = self._idx(key)
        for idx, entry in enumerate(self.buckets[i]):
            if entry[0] == key:
                del self.buckets[i][idx]
                self._size -= 1
                return True
        return False
    def __len__(self):
        return self._size

class SlabCache:
    """Simplified slab allocator: maintains lists of fixed-size objects."""
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self.partial: deque = deque()   # slabs with free objects
        self.full: deque = deque()
        self.free_objs: deque = deque()
    def alloc(self) -> Optional[Any]:
        if self.free_objs:
            return self.free_objs.popleft()
        obj = {"slab_name": self.name, "payload": bytearray(self.size)}
        return obj
    def free(self, obj: Any):
        self.free_objs.append(obj)
    def __repr__(self):
        return f"SlabCache({self.name},partial={len(self.partial)},free={len(self.free_objs)})"


# ============================================================================
# 2. CORE ENGINE — Scheduler, Memory, VFS, Syscalls
# ============================================================================

class ProcessScheduler:
    """CFS-like Completely Fair Scheduler simulation."""
    def __init__(self):
        self.tasks: Dict[int, task_struct] = {}
        self.cfs_rq = RBTree()          # runqueue ordered by vruntime
        self.nr_running = 0
        self.min_vruntime = 0
        self.next_pid = 1
        self.current: Optional[task_struct] = None
        self.nice_to_weight = [88761, 71755, 56483, 46273, 36291,
                               29154, 23254, 18705, 14949, 11916,
                               9548, 7620, 6100, 4904, 3906,
                               3121, 2501, 1991, 1586, 1277, 1024,
                               820, 655, 526, 423, 335, 272, 215,
                               172, 137, 110]
    def _weight(self, prio: int) -> int:
        nice = prio - 120
        idx = max(0, min(40, nice + 20))
        return self.nice_to_weight[idx]
    def wake_up_new_task(self, t: task_struct):
        t.vruntime = self.min_vruntime
        self.tasks[t.pid] = t
        self.cfs_rq.insert(t.vruntime, t)
        self.nr_running += 1
        printk(f"sched: wake_up_new_task pid={t.pid} comm={t.comm} vr={t.vruntime}")
    def task_tick(self):
        """Called on each timer tick; charges vruntime."""
        if self.current:
            weight = self._weight(self.current.prio)
            delta = 1024 * 1024 // weight   # simulated time slice charge
            self.current.vruntime += delta
            # re-insert if not only task
            if self.nr_running > 1:
                self.cfs_rq.remove_min()
                self.cfs_rq.insert(self.current.vruntime, self.current)
    def schedule(self) -> Optional[task_struct]:
        if self.nr_running == 0:
            self.current = None
            return None
        # In real kernel schedule() is complex; here pick leftmost (min vruntime)
        res = self.cfs_rq.find_min()
        if res:
            _, nxt = res
            if nxt != self.current:
                printk(f"sched: context_switch {self.current} -> {nxt}")
                self.current = nxt
                self.min_vruntime = nxt.vruntime
            return nxt
        return None
    def fork_task(self, parent: task_struct, comm: str = "") -> task_struct:
        child = task_struct(self.next_pid, comm or f"{parent.comm}_child")
        self.next_pid += 1
        child.parent = parent
        child.mm = parent.mm  # share mm (copy-on-write later)
        parent.children.append(child)
        self.wake_up_new_task(child)
        return child
    def __repr__(self):
        return f"ProcessScheduler(nr={self.nr_running},cur={self.current})"

class MemoryManager:
    """Simulates paging, VMAs, page fault handling, and slab."""
    def __init__(self):
        self.pages: Dict[int, page] = {}
        self.pfn_counter = 0
        self.slab_caches: Dict[str, SlabCache] = {}
        self.page_size = 4096
    def alloc_page(self) -> page:
        p = page(self.pfn_counter)
        self.pfn_counter += 1
        self.pages[p.pfn] = p
        p.refcount.inc()
        return p
    def free_page(self, p: page):
        p.refcount.dec()
        if p.refcount.read() <= 0:
            del self.pages[p.pfn]
    def find_vma(self, mm: mm_struct, addr: int) -> Optional[vm_area_struct]:
        vma = mm.mmap
        while vma:
            if vma.vm_start <= addr < vma.vm_end:
                return vma
            vma = vma.vm_next
        return None
    def insert_vm_struct(self, mm: mm_struct, vma: vm_area_struct):
        vma.vm_mm = mm
        if not mm.mmap:
            mm.mmap = vma
        else:
            cur = mm.mmap
            while cur.vm_next:
                cur = cur.vm_next
            cur.vm_next = vma
        mm.total_vm += (vma.vm_end - vma.vm_start) // self.page_size
    def handle_mm_fault(self, mm: mm_struct, addr: int, write: bool = False) -> bool:
        """Page fault handler: allocate page for missing VMA entry."""
        vma = self.find_vma(mm, addr)
        if not vma:
            printk(f"mm: segfault at 0x{addr:x}")
            return False
        pg = self.alloc_page()
        pg.mapping = vma
        printk(f"mm: page_fault handled addr=0x{addr:x} pfn={pg.pfn} write={write}")
        return True
    def new_slab(self, name: str, size: int) -> SlabCache:
        sc = SlabCache(name, size)
        self.slab_caches[name] = sc
        return sc
    def __repr__(self):
        return f"MemoryManager(pages={len(self.pages)},slabs={list(self.slab_caches.keys())})"

class VirtualFileSystem:
    """VFS layer: superblock, inode cache, dentry cache, path walk."""
    def __init__(self):
        self.mounts: Dict[str, super_block] = {}
        self.dentry_cache = HashTable(128)
        self.inode_cache = HashTable(128)
        self.root_dentry: Optional[dentry] = None
    def alloc_inode(self, sb: super_block) -> inode:
        i = inode(len(self.inode_cache.buckets))  # simplistic numbering
        i.i_sb = sb
        sb.s_inodes[i.i_ino] = i
        self.inode_cache.put(i.i_ino, i)
        return i
    def d_alloc(self, parent: dentry, name: str) -> dentry:
        d = dentry(name, parent)
        parent.d_subdirs[name] = d
        key = f"{id(parent)}:{name}"
        self.dentry_cache.put(key, d)
        return d
    def mount_fs(self, path: str, fstype: str = "ext4") -> super_block:
        sb = super_block(path, fstype)
        root = dentry("/")
        sb.s_root = root
        root.d_inode = self.alloc_inode(sb)
        self.mounts[path] = sb
        if path == "/":
            self.root_dentry = root
        printk(f"vfs: mounted {fstype} at {path}")
        return sb
    def path_walk(self, path: str) -> Optional[dentry]:
        if not self.root_dentry:
            return None
        if path == "/":
            return self.root_dentry
        parts = [p for p in path.split("/") if p]
        cur = self.root_dentry
        for part in parts:
            if part == "..":
                cur = cur.d_parent if cur.d_parent else cur
            elif part in cur.d_subdirs:
                cur = cur.d_subdirs[part]
            else:
                return None
        return cur
    def create_file(self, parent_path: str, name: str) -> dentry:
        parent = self.path_walk(parent_path)
        if not parent:
            raise ValueError(f"No such path: {parent_path}")
        d = self.d_alloc(parent, name)
        d.d_inode = self.alloc_inode(parent.d_inode.i_sb)
        printk(f"vfs: created {parent_path}/{name} inode={d.d_inode.i_ino}")
        return d
    def __repr__(self):
        return f"VFS(mounts={list(self.mounts.keys())})"

class SyscallTrap:
    """System call table and trap handler simulation."""
    def __init__(self, sched: ProcessScheduler, mm: MemoryManager, vfs: VirtualFileSystem):
        self.sched = sched
        self.mm = mm
        self.vfs = vfs
        self.table: Dict[int, Callable[..., Any]] = {}
        self._build_table()
    def _build_table(self):
        self.table[2] = self.sys_fork    # __NR_fork historically
        self.table[11] = self.sys_execve # __NR_execve historically
        self.table[0] = self.sys_read    # __NR_read
        self.table[1] = self.sys_write   # __NR_write
    def sys_fork(self, parent: task_struct) -> int:
        child = self.sched.fork_task(parent, comm=parent.comm)
        printk(f"syscall: fork() pid={parent.pid} -> child={child.pid}")
        return child.pid
    def sys_execve(self, t: task_struct, path: str):
        # Simulate exec: replace mm with new one (simplified)
        new_mm = mm_struct()
        t.mm = new_mm
        t.comm = path.split("/")[-1]
        # allocate stack VMA
        stack_vma = vm_area_struct(0x7fff0000, 0x7fff1000, flags=0x2)
        self.mm.insert_vm_struct(new_mm, stack_vma)
        printk(f"syscall: execve({path}) pid={t.pid} new_mm allocated")
        return 0
    def sys_read(self, fd: int, buf_addr: int, count: int) -> int:
        # Simulate reading into a page
        return count
    def sys_write(self, fd: int, buf_addr: int, count: int) -> int:
        return count
    def handle(self, nr: int, *args) -> Any:
        if nr in self.table:
            return self.table[nr](*args)
        printk(f"syscall: unimplemented {nr}")
        return -38  # ENOSYS
    def __repr__(self):
        return f"SyscallTrap(syscalls={list(self.table.keys())})"


# ============================================================================
# 3. FEATURES — Networking, Interrupts, Module Loader, Boot
# ============================================================================

class TCPState(enum.Enum):
    CLOSED = 0
    LISTEN = 1
    SYN_SENT = 2
    SYN_RECV = 3
    ESTABLISHED = 4
    FIN_WAIT1 = 5
    FIN_WAIT2 = 6
    CLOSE_WAIT = 7
    CLOSING = 8
    LAST_ACK = 9
    TIME_WAIT = 10

class sock:
    """Socket representation with TCP state machine."""
    def __init__(self, family: int = 2, stype: int = 1):
        self.family = family
        self.stype = stype
        self.state = TCPState.CLOSED
        self.sk_receive_queue: deque = deque()
        self.sk_write_queue: deque = deque()
        self.saddr = "0.0.0.0"
        self.sport = 0
        self.daddr = "0.0.0.0"
        self.dport = 0
    def __repr__(self):
        return f"sock(state={self.state.name})"

class NetworkingStack:
    """TCP/IP stack simulation: sk_buff chains, state machine, routing."""
    def __init__(self):
        self.sockets: List[sock] = []
        self.routes: List[Tuple[str, str, str]] = []  # (dest, mask, gateway)
    def tcp_v4_connect(self, sk: sock, daddr: str, dport: int) -> int:
        sk.daddr = daddr
        sk.dport = dport
        sk.state = TCPState.SYN_SENT
        # simulate sending SYN
        syn = sk_buff(b"SYN")
        syn.saddr = sk.saddr
        syn.daddr = daddr
        syn.dport = dport
        sk.sk_write_queue.append(syn)
        printk(f"net: tcp_connect -> SYN_SENT to {daddr}:{dport}")
        return 0
    def tcp_rcv_established(self, sk: sock, skb: sk_buff) -> None:
        pkt = skb.data.decode("latin1", errors="ignore")
        if "SYN" in pkt and "ACK" in pkt:
            if sk.state == TCPState.SYN_SENT:
                sk.state = TCPState.ESTABLISHED
                printk(f"net: received SYN-ACK, state -> ESTABLISHED")
                # send ACK
                ack = sk_buff(b"ACK")
                sk.sk_write_queue.append(ack)
        elif "FIN" in pkt:
            if sk.state == TCPState.ESTABLISHED:
                sk.state = TCPState.CLOSE_WAIT
                printk("net: received FIN, state -> CLOSE_WAIT")
    def route_lookup(self, daddr: str) -> Optional[str]:
        for dest, mask, gw in self.routes:
            # simplistic string prefix match simulation
            if daddr.startswith(dest.rsplit(".", 1)[0]):
                return gw
        return "0.0.0.0"
    def add_route(self, dest: str, mask: str, gw: str):
        self.routes.append((dest, mask, gw))
    def __repr__(self):
        return f"NetworkingStack(sockets={len(self.sockets)},routes={len(self.routes)})"

class InterruptController:
    """IRQ descriptor table, top-half/bottom-half handling, softirq."""
    def __init__(self, sched: ProcessScheduler):
        self.sched = sched
        self.irq_table: Dict[int, Callable[..., Any]] = {}
        self.softirq_pending: deque = deque()
        self.tasklet_queue: deque = deque()
        self.jiffies = 0
        self._register_irqs()
    def _register_irqs(self):
        self.irq_table[0] = self._irq_timer   # IRQ0 = timer
        self.irq_table[1] = self._irq_kb      # IRQ1 = keyboard (stub)
    def _irq_timer(self):
        self.jiffies += 1
        self.sched.task_tick()
        # raise TIMER softirq
        self.softirq_pending.append("TIMER")
    def _irq_kb(self):
        self.softirq_pending.append("KEYBOARD")
    def handle_IRQ(self, irq: int):
        """Top-half: immediate, hardware-context-like."""
        if irq in self.irq_table:
            printk(f"irq: top-half IRQ{irq}")
            self.irq_table[irq]()
        else:
            printk(f"irq: spurious IRQ{irq}")
    def do_softirq(self):
        """Bottom-half: deferred processing."""
        while self.softirq_pending:
            s = self.softirq_pending.popleft()
            if s == "TIMER":
                # run scheduler bottom half
                self.sched.schedule()
            elif s == "KEYBOARD":
                printk("softirq: keyboard bh processed")
    def raise_softirq(self, name: str):
        self.softirq_pending.append(name)
    def __repr__(self):
        return f"InterruptController(jiffies={self.jiffies},softirqs={len(self.softirq_pending)})"

class ModuleLoader:
    """Kernel module loading with symbol resolution and dependency graph."""
    def __init__(self):
        self.symbols: Dict[str, Any] = {}  # global kernel symbol table
        self.modules: Dict[str, Dict[str, Any]] = {}
    def export_symbol(self, name: str, val: Any):
        self.symbols[name] = val
    def load_module(self, name: str, deps: List[str], syms: Dict[str, Any]):
        # topological check: deps must already be loaded
        for d in deps:
            if d not in self.modules:
                raise RuntimeError(f"module {name}: missing dependency {d}")
        self.modules[name] = {"deps": deps, "syms": syms, "state": "loaded"}
        # resolve and register module symbols into global table
        for s, v in syms.items():
            self.symbols[f"{name}:{s}"] = v
        printk(f"mod: loaded {name} deps={deps}")
    def resolve_symbols(self, name: str, needed: List[str]) -> Dict[str, Any]:
        out = {}
        for n in needed:
            if n in self.symbols:
                out[n] = self.symbols[n]
            else:
                raise RuntimeError(f"module {name}: unresolved {n}")
        return out
    def __repr__(self):
        return f"ModuleLoader(mods={list(self.modules.keys())},syms={len(self.symbols)})"

class BootProcess:
    """Simulates boot: GRUB stages, initrd, init process."""
    def __init__(self, sched: ProcessScheduler, mm: MemoryManager, vfs: VirtualFileSystem, net: NetworkingStack):
        self.sched = sched
        self.mm = mm
        self.vfs = vfs
        self.net = net
        self.stage = "poweroff"
    def grub_stage1(self):
        self.stage = "grub_stage1"
        printk("boot: GRUB Stage 1 — MBR bootstrap loader")
    def grub_stage2(self):
        self.stage = "grub_stage2"
        printk("boot: GRUB Stage 2 — filesystem aware, load kernel + initrd")
    def load_initrd(self):
        self.stage = "initrd"
        printk("boot: initrd loaded — temporary rootfs with essential modules")
        # create a minimal tmpfs-like tree in VFS
        self.vfs.mount_fs("/", "tmpfs")
        self.vfs.create_file("/", "init")
        self.vfs.create_file("/", "linuxrc")
    def start_init(self):
        self.stage = "init"
        init_task = task_struct(self.sched.next_pid, "init")
        self.sched.next_pid += 1
        init_task.mm = mm_struct()
        # setup std init VMAs
        code_vma = vm_area_struct(0x400000, 0x401000, flags=0x1)
        self.mm.insert_vm_struct(init_task.mm, code_vma)
        self.sched.wake_up_new_task(init_task)
        self.sched.current = init_task
        printk("boot: init process spawned (pid=1 equivalent)")
    def full_boot(self):
        self.grub_stage1()
        self.grub_stage2()
        self.load_initrd()
        self.start_init()
    def __repr__(self):
        return f"BootProcess(stage={self.stage})"


# ============================================================================
# 4. KERNEL + DEMOS
# ============================================================================

class LinuxInsidesKernel:
    """Main kernel class that wires all subsystems together."""
    def __init__(self):
        self.sched = ProcessScheduler()
        self.mm = MemoryManager()
        self.vfs = VirtualFileSystem()
        self.net = NetworkingStack()
        self.irq = InterruptController(self.sched)
        self.modules = ModuleLoader()
        self.boot = BootProcess(self.sched, self.mm, self.vfs, self.net)
        self.syscall = SyscallTrap(self.sched, self.mm, self.vfs)
        printk("kernel: LinuxInsidesKernel initialized")
    def timer_tick(self):
        self.irq.handle_IRQ(0)
        self.irq.do_softirq()
    def __repr__(self):
        return (f"LinuxInsidesKernel(sched={self.sched},mm={self.mm},"
                f"vfs={self.vfs},net={self.net},irq={self.irq})")


def demo_fork_exec():
    printk("\n=== DEMO: fork/exec ===")
    k = LinuxInsidesKernel()
    parent = task_struct(k.sched.next_pid, "bash")
    k.sched.next_pid += 1
    parent.mm = mm_struct()
    k.sched.wake_up_new_task(parent)
    k.sched.current = parent
    k.syscall.sys_fork(parent)
    k.syscall.sys_execve(parent, "/bin/ls")
    k.timer_tick()
    printk(f"fork/exec result: {k.sched}")

def demo_page_fault():
    printk("\n=== DEMO: page fault + COW ===")
    k = LinuxInsidesKernel()
    t = task_struct(k.sched.next_pid, "app")
    k.sched.next_pid += 1
    t.mm = mm_struct()
    vma = vm_area_struct(0x7f000000, 0x7f001000, flags=0x2)
    k.mm.insert_vm_struct(t.mm, vma)
    # simulate access causing page fault
    k.mm.handle_mm_fault(t.mm, 0x7f000500, write=True)
    # simulate COW: fork then child writes
    child = k.sched.fork_task(t)
    # child write triggers another fault (COW break)
    k.mm.handle_mm_fault(child.mm, 0x7f000500, write=True)
    printk(f"page_fault result: {k.mm}")

def demo_vfs_walk():
    printk("\n=== DEMO: VFS path walk ===")
    k = LinuxInsidesKernel()
    k.vfs.mount_fs("/", "ext4")
    k.vfs.create_file("/", "home")
    home = k.vfs.path_walk("/home")
    # in our simple model /home is a file not a dir; create subdirs via create_file on parent
    k.vfs.create_file("/", "home")  # re-creating is a no-op in simple model; adapt
    # Build /home/user/file.txt manually via d_alloc
    root = k.vfs.root_dentry
    home_d = k.vfs.d_alloc(root, "home")
    user_d = k.vfs.d_alloc(home_d, "user")
    file_d = k.vfs.d_alloc(user_d, "file.txt")
    file_d.d_inode = k.vfs.alloc_inode(root.d_inode.i_sb)
    target = k.vfs.path_walk("/home/user/file.txt")
    printk(f"vfs walk result: {target}")
    assert target is file_d, "VFS walk failed"

def demo_tcp_handshake():
    printk("\n=== DEMO: TCP 3-way handshake ===")
    k = LinuxInsidesKernel()
    sk = sock()
    sk.saddr = "192.168.1.2"
    k.net.sockets.append(sk)
    k.net.tcp_v4_connect(sk, "192.168.1.1", 80)
    # Simulate receiving SYN-ACK
    synack = sk_buff(b"SYN+ACK")
    synack.saddr = "192.168.1.1"
    synack.daddr = sk.saddr
    k.net.tcp_rcv_established(sk, synack)
    printk(f"tcp handshake result: {sk}")
    assert sk.state == TCPState.ESTABLISHED

def demo_module_load():
    printk("\n=== DEMO: kernel module dependency load ===")
    k = LinuxInsidesKernel()
    # module_a exports helper_fn
    k.modules.export_symbol("helper_fn", lambda x: x * 2)
    # module_b depends on module_a
    k.modules.load_module("module_a", [], {"helper_fn": lambda x: x * 2})
    k.modules.load_module("module_b", ["module_a"], {"use_helper": "refs helper_fn"})
    resolved = k.modules.resolve_symbols("module_b", ["helper_fn"])
    printk(f"module load result: resolved={list(resolved.keys())}, {k.modules}")

def demo_boot_sequence():
    printk("\n=== DEMO: full boot sequence ===")
    k = LinuxInsidesKernel()
    k.boot.full_boot()
    # simulate a few timer ticks post-boot
    for _ in range(3):
        k.timer_tick()
    printk(f"boot result: {k.boot}, current={k.sched.current}")


if __name__ == "__main__":
    print("=" * 70)
    print(" Linux Kernel Internals Simulation — linux_insides_native.py ")
    print("=" * 70)
    demo_fork_exec()
    demo_page_fault()
    demo_vfs_walk()
    demo_tcp_handshake()
    demo_module_load()
    demo_boot_sequence()
    print("\n" + "=" * 70)
    print(" All demos completed successfully.")
    print("=" * 70)
