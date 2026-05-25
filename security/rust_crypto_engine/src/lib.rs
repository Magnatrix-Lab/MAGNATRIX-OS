/// MAGNATRIX-OS — Rust Cryptographic Engine
/// Provides: hashing, signing, AEAD encryption, key derivation, KDF
/// Exposed to Python via PyO3
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use rand::rngs::OsRng;
use sha2::{Sha256, Sha512, Digest};
use sha3::Sha3_256;
use blake3;
use ed25519_dalek::{Signer, SigningKey, Signature, VerifyingKey};
use chacha20poly1305::{
    ChaCha20Poly1305, Nonce,
    aead::{Aead, KeyInit, AeadCore},
};
use aes_gcm::{
    Aes256Gcm,
    aead::{Aead as AesAead, KeyInit as AesKeyInit},
};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{SaltString, rand_core::RngCore};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use zeroize::Zeroize;

// ═══════════════════════════════════════════════════════════════════════════════
// Hashing
// ═══════════════════════════════════════════════════════════════════════════════

#[pyfunction]
fn sha256(data: &[u8]) -> Vec<u8> {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

#[pyfunction]
fn sha512(data: &[u8]) -> Vec<u8> {
    let mut hasher = Sha512::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

#[pyfunction]
fn sha3_256(data: &[u8]) -> Vec<u8> {
    let mut hasher = Sha3_256::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

#[pyfunction]
fn blake3_hash(data: &[u8]) -> Vec<u8> {
    blake3::hash(data).as_bytes().to_vec()
}

#[pyfunction]
fn hmac_sha256(key: &[u8], data: &[u8]) -> Vec<u8> {
    use hmac::Mac;
    type HmacSha256 = hmac::Hmac<Sha256>;
    let mut mac = HmacSha256::new_from_slice(key).expect("HMAC can take key of any size");
    mac.update(data);
    mac.finalize().into_bytes().to_vec()
}

// ═══════════════════════════════════════════════════════════════════════════════
// Ed25519 Signing
// ═══════════════════════════════════════════════════════════════════════════════

#[pyclass]
struct Ed25519Keypair {
    signing_key: Option<SigningKey>,
}

#[pymethods]
impl Ed25519Keypair {
    #[new]
    fn new() -> Self {
        let mut csprng = OsRng;
        let signing_key = SigningKey::generate(&mut csprng);
        Self { signing_key: Some(signing_key) }
    }

    #[staticmethod]
    fn from_seed(seed: &[u8]) -> PyResult<Self> {
        if seed.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Ed25519 seed must be 32 bytes"
            ));
        }
        let mut bytes = [0u8; 32];
        bytes.copy_from_slice(seed);
        let signing_key = SigningKey::from_bytes(&bytes);
        Ok(Self { signing_key: Some(signing_key) })
    }

    fn sign<'py>(&self, py: Python<'py>, message: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let sk = self.signing_key.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Keypair not initialized"))?;
        let signature = sk.sign(message);
        Ok(PyBytes::new(py, signature.as_bytes()))
    }

    fn public_key<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let sk = self.signing_key.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Keypair not initialized"))?;
        let vk = sk.verifying_key();
        Ok(PyBytes::new(py, vk.as_bytes()))
    }

    fn secret_key<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let sk = self.signing_key.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Keypair not initialized"))?;
        Ok(PyBytes::new(py, sk.as_bytes()))
    }
}

#[pyfunction]
fn ed25519_verify(public_key: &[u8], message: &[u8], signature: &[u8]) -> PyResult<bool> {
    if public_key.len() != 32 {
        return Err(pyo3::exceptions::PyValueError::new_err("Public key must be 32 bytes"));
    }
    if signature.len() != 64 {
        return Err(pyo3::exceptions::PyValueError::new_err("Signature must be 64 bytes"));
    }
    let vk_bytes: [u8; 32] = public_key.try_into()
        .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid public key length"))?;
    let vk = VerifyingKey::from_bytes(&vk_bytes)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid public key: {}", e)))?;
    let sig_bytes: [u8; 64] = signature.try_into()
        .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid signature length"))?;
    let sig = Signature::from_bytes(&sig_bytes);
    Ok(vk.verify(message, &sig).is_ok())
}

// ═══════════════════════════════════════════════════════════════════════════════
// ChaCha20-Poly1305 AEAD
// ═══════════════════════════════════════════════════════════════════════════════

#[pyclass]
struct ChaChaCipher {
    cipher: ChaCha20Poly1305,
}

#[pymethods]
impl ChaChaCipher {
    #[new]
    fn new(key: &[u8]) -> PyResult<Self> {
        if key.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err("ChaCha20 key must be 32 bytes"));
        }
        let cipher = ChaCha20Poly1305::new_from_slice(key)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Key init error: {}", e)))?;
        Ok(Self { cipher })
    }

    fn encrypt<'py>(&self, py: Python<'py>, plaintext: &[u8], nonce: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        if nonce.len() != 12 {
            return Err(pyo3::exceptions::PyValueError::new_err("Nonce must be 12 bytes"));
        }
        let nonce_arr = Nonce::from_slice(nonce);
        let ciphertext = self.cipher.encrypt(nonce_arr, plaintext.as_ref())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Encryption failed: {}", e)))?;
        Ok(PyBytes::new(py, &ciphertext))
    }

    fn decrypt<'py>(&self, py: Python<'py>, ciphertext: &[u8], nonce: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        if nonce.len() != 12 {
            return Err(pyo3::exceptions::PyValueError::new_err("Nonce must be 12 bytes"));
        }
        let nonce_arr = Nonce::from_slice(nonce);
        let plaintext = self.cipher.decrypt(nonce_arr, ciphertext.as_ref())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Decryption failed: {}", e)))?;
        Ok(PyBytes::new(py, &plaintext))
    }

    #[staticmethod]
    fn generate_nonce<'py>(py: Python<'py>) -> Bound<'py, PyBytes> {
        let nonce = ChaCha20Poly1305::generate_nonce(&mut OsRng);
        PyBytes::new(py, nonce.as_slice())
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// AES-256-GCM
// ═══════════════════════════════════════════════════════════════════════════════

#[pyclass]
struct Aes256GcmCipher {
    cipher: Aes256Gcm,
}

#[pymethods]
impl Aes256GcmCipher {
    #[new]
    fn new(key: &[u8]) -> PyResult<Self> {
        if key.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err("AES-256 key must be 32 bytes"));
        }
        let cipher = Aes256Gcm::new_from_slice(key)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Key init error: {}", e)))?;
        Ok(Self { cipher })
    }

    fn encrypt<'py>(&self, py: Python<'py>, plaintext: &[u8], nonce: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        if nonce.len() != 12 {
            return Err(pyo3::exceptions::PyValueError::new_err("Nonce must be 12 bytes"));
        }
        let nonce_arr = aes_gcm::Nonce::from_slice(nonce);
        let ciphertext = self.cipher.encrypt(nonce_arr, plaintext.as_ref())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Encryption failed: {}", e)))?;
        Ok(PyBytes::new(py, &ciphertext))
    }

    fn decrypt<'py>(&self, py: Python<'py>, ciphertext: &[u8], nonce: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        if nonce.len() != 12 {
            return Err(pyo3::exceptions::PyValueError::new_err("Nonce must be 12 bytes"));
        }
        let nonce_arr = aes_gcm::Nonce::from_slice(nonce);
        let plaintext = self.cipher.decrypt(nonce_arr, ciphertext.as_ref())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Decryption failed: {}", e)))?;
        Ok(PyBytes::new(py, &plaintext))
    }

    #[staticmethod]
    fn generate_nonce<'py>(py: Python<'py>) -> Bound<'py, PyBytes> {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        PyBytes::new(py, nonce.as_slice())
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Argon2 Password Hashing
// ═══════════════════════════════════════════════════════════════════════════════

#[pyfunction]
fn argon2_hash_password(password: &str) -> PyResult<String> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();
    let password_hash = argon2.hash_password(password.as_bytes(), &salt)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Hashing failed: {}", e)))?;
    Ok(password_hash.to_string())
}

#[pyfunction]
fn argon2_verify_password(password: &str, hash: &str) -> PyResult<bool> {
    let parsed_hash = PasswordHash::new(hash)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid hash: {}", e)))?;
    let argon2 = Argon2::default();
    Ok(argon2.verify_password(password.as_bytes(), &parsed_hash).is_ok())
}

#[pyfunction]
fn argon2_derive_key(password: &str, salt: &[u8], length: usize) -> PyResult<Vec<u8>> {
    if length > 64 {
        return Err(pyo3::exceptions::PyValueError::new_err("Max key length is 64 bytes"));
    }
    let mut output = vec![0u8; length];
    let argon2 = Argon2::default();
    argon2.hash_password_into(password.as_bytes(), salt, &mut output)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("KDF failed: {}", e)))?;
    Ok(output)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Secure Random
// ═══════════════════════════════════════════════════════════════════════════════

#[pyfunction]
fn secure_random_bytes<'py>(py: Python<'py>, length: usize) -> Bound<'py, PyBytes> {
    let mut buf = vec![0u8; length];
    OsRng.fill_bytes(&mut buf);
    PyBytes::new(py, &buf)
}

#[pyfunction]
fn secure_random_u64() -> u64 {
    let mut buf = [0u8; 8];
    OsRng.fill_bytes(&mut buf);
    u64::from_le_bytes(buf)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Base64 / Hex helpers
// ═══════════════════════════════════════════════════════════════════════════════

#[pyfunction]
fn b64_encode(data: &[u8]) -> String {
    BASE64.encode(data)
}

#[pyfunction]
fn b64_decode(data: &str) -> PyResult<Vec<u8>> {
    BASE64.decode(data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Base64 decode error: {}", e)))
}

#[pyfunction]
fn hex_encode(data: &[u8]) -> String {
    hex::encode(data)
}

#[pyfunction]
fn hex_decode(data: &str) -> PyResult<Vec<u8>> {
    hex::decode(data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Hex decode error: {}", e)))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Module definition
// ═══════════════════════════════════════════════════════════════════════════════

#[pymodule]
fn _magnatrix_crypto(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.9.5")?;
    m.add("__backend__", "rust")?;

    // Hashing
    m.add_wrapped(wrap_pyfunction!(sha256))?;
    m.add_wrapped(wrap_pyfunction!(sha512))?;
    m.add_wrapped(wrap_pyfunction!(sha3_256))?;
    m.add_wrapped(wrap_pyfunction!(blake3_hash))?;
    m.add_wrapped(wrap_pyfunction!(hmac_sha256))?;

    // Signing
    m.add_class::<Ed25519Keypair>()?;
    m.add_wrapped(wrap_pyfunction!(ed25519_verify))?;

    // Encryption
    m.add_class::<ChaChaCipher>()?;
    m.add_class::<Aes256GcmCipher>()?;

    // KDF
    m.add_wrapped(wrap_pyfunction!(argon2_hash_password))?;
    m.add_wrapped(wrap_pyfunction!(argon2_verify_password))?;
    m.add_wrapped(wrap_pyfunction!(argon2_derive_key))?;

    // Random
    m.add_wrapped(wrap_pyfunction!(secure_random_bytes))?;
    m.add_wrapped(wrap_pyfunction!(secure_random_u64))?;

    // Encoding
    m.add_wrapped(wrap_pyfunction!(b64_encode))?;
    m.add_wrapped(wrap_pyfunction!(b64_decode))?;
    m.add_wrapped(wrap_pyfunction!(hex_encode))?;
    m.add_wrapped(wrap_pyfunction!(hex_decode))?;

    Ok(())
}
