package protocol

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdh"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	xhkdf "golang.org/x/crypto/hkdf"
)

const (
	// 4-byte big-endian framing is used for payload length.
	frameLenSize = 4
	// Nonce size for AES-GCM
	nonceSize = 12
)

var (
	// Magic preface for ECDH handshake (server -> client first)
	kexMagic = []byte("PPKX\x01")
	// HKDF info string to match Python side
	hkdfInfo  = []byte("PrometheanProxy/MP_ECDH_v1")
)

// SecureConn wraps a net.Conn and transparently adds app-layer ECDH + AES-GCM
// encryption and HMAC-SHA256 signing for each message when keys are established.
type SecureConn struct {
	net.Conn
	encKey []byte
	macKey []byte
}

// UpgradeToSecure performs the client-side ECDH (X25519) handshake over an
// already-established (e.g., TLS) connection and returns a SecureConn.
func UpgradeToSecure(conn net.Conn) (*SecureConn, error) {
	sc := &SecureConn{Conn: conn}
	if err := sc.HandshakeClient(); err != nil {
		return nil, err
	}
	return sc, nil
}

// HandshakeClient implements: read magic+serverPub, send clientPub, derive keys.
func (sc *SecureConn) HandshakeClient() error {
	if sc.Conn == nil {
		return errors.New("nil connection")
	}
	// Read magic
	magic := make([]byte, len(kexMagic))
	if _, err := io.ReadFull(sc.Conn, magic); err != nil {
		return fmt.Errorf("failed reading handshake magic: %w", err)
	}
	if string(magic) != string(kexMagic) {
		return errors.New("invalid ECDH handshake preface")
	}

	// Read server pub (32 bytes for X25519)
	srvPub := make([]byte, 32)
	if _, err := io.ReadFull(sc.Conn, srvPub); err != nil {
		return fmt.Errorf("failed reading server pub: %w", err)
	}

	curve := ecdh.X25519()
	priv, err := curve.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("failed generating client key: %w", err)
	}
	// Send client public bytes
	if _, err := sc.Conn.Write(priv.PublicKey().Bytes()); err != nil {
		return fmt.Errorf("failed sending client pub: %w", err)
	}

	peer, err := curve.NewPublicKey(srvPub)
	if err != nil {
		return fmt.Errorf("invalid server public key: %w", err)
	}
	shared, err := priv.ECDH(peer)
	if err != nil {
		return fmt.Errorf("ECDH failed: %w", err)
	}

	enc, mac, err := deriveKeys(shared)
	if err != nil {
		return err
	}
	sc.encKey, sc.macKey = enc, mac
	return nil
}

// HandshakeServer (optional) for server roles in Go, matching Python format.
func (sc *SecureConn) HandshakeServer() error {
	if sc.Conn == nil {
		return errors.New("nil connection")
	}
	curve := ecdh.X25519()
	priv, err := curve.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("failed generating server key: %w", err)
	}
	// Send magic + server pub
	if _, err := sc.Conn.Write(append(kexMagic, priv.PublicKey().Bytes()...)); err != nil {
		return fmt.Errorf("failed sending handshake preface: %w", err)
	}
	// Read client pub
	cliPub := make([]byte, 32)
	if _, err := io.ReadFull(sc.Conn, cliPub); err != nil {
		return fmt.Errorf("failed reading client pub: %w", err)
	}
	peer, err := curve.NewPublicKey(cliPub)
	if err != nil {
		return fmt.Errorf("invalid client public key: %w", err)
	}
	shared, err := priv.ECDH(peer)
	if err != nil {
		return fmt.Errorf("ECDH failed: %w", err)
	}
	enc, mac, err := deriveKeys(shared)
	if err != nil {
		return err
	}
	sc.encKey, sc.macKey = enc, mac
	return nil
}

func deriveKeys(shared []byte) (encKey, macKey []byte, err error) {
	// HKDF-SHA256, 64 bytes, split into 32B enc + 32B mac
	rdr := xhkdf.New(sha256.New, shared, nil, hkdfInfo)
	out := make([]byte, 64)
	if _, err = io.ReadFull(rdr, out); err != nil {
		return nil, nil, fmt.Errorf("hkdf derive: %w", err)
	}
	return out[:32], out[32:], nil
}

// Send sends data with optional AES-GCM encryption and HMAC-SHA256 tag.
// Framing:
//   enc+mac: [4B len(blob)] [blob=nonce(12)|ciphertext] [32B tag=HMAC(blob)]
//   mac only: [4B len(payload)] [payload] [32B tag=HMAC(payload)]
//   none:     [4B len(payload)] [payload]
func (sc *SecureConn) Send(data []byte) error {
	if sc.encKey != nil {
		block, err := aes.NewCipher(sc.encKey)
		if err != nil {
			return fmt.Errorf("aes cipher: %w", err)
		}
		aead, err := cipher.NewGCM(block)
		if err != nil {
			return fmt.Errorf("gcm: %w", err)
		}
		nonce := make([]byte, nonceSize)
		if _, err := rand.Read(nonce); err != nil {
			return fmt.Errorf("nonce: %w", err)
		}
		ct := aead.Seal(nil, nonce, data, nil)
		blob := append(nonce, ct...)
		// length
		lenBuf := make([]byte, frameLenSize)
		binary.BigEndian.PutUint32(lenBuf, uint32(len(blob)))
		if _, err := sc.Conn.Write(lenBuf); err != nil {
			return fmt.Errorf("write len: %w", err)
		}
		if _, err := sc.Conn.Write(blob); err != nil {
			return fmt.Errorf("write blob: %w", err)
		}
		if sc.macKey != nil {
			h := hmac.New(sha256.New, sc.macKey)
			h.Write(blob)
			if _, err := sc.Conn.Write(h.Sum(nil)); err != nil {
				return fmt.Errorf("write hmac: %w", err)
			}
		}
		return nil
	}

	// No encryption path
	lenBuf := make([]byte, frameLenSize)
	binary.BigEndian.PutUint32(lenBuf, uint32(len(data)))
	if _, err := sc.Conn.Write(lenBuf); err != nil {
		return fmt.Errorf("write len: %w", err)
	}
	if _, err := sc.Conn.Write(data); err != nil {
		return fmt.Errorf("write payload: %w", err)
	}
	if sc.macKey != nil {
		h := hmac.New(sha256.New, sc.macKey)
		h.Write(data)
		if _, err := sc.Conn.Write(h.Sum(nil)); err != nil {
			return fmt.Errorf("write hmac: %w", err)
		}
	}
	return nil
}

// Receive reads a single framed message and returns the payload bytes.
// Decrypts and/or validates HMAC depending on configured keys.
func (sc *SecureConn) Receive() ([]byte, error) {
	lenBuf := make([]byte, frameLenSize)
	if _, err := io.ReadFull(sc.Conn, lenBuf); err != nil {
		if err == io.EOF {
			return nil, fmt.Errorf("connection closed by peer while reading length: %w", err)
		}
		return nil, fmt.Errorf("read length: %w", err)
	}
	total := binary.BigEndian.Uint32(lenBuf)
	if total == 0 {
		// still might have a MAC to read, but with zero payload that is unusual; ignore for now
		return []byte{}, nil
	}
	blob := make([]byte, total)
	if _, err := io.ReadFull(sc.Conn, blob); err != nil {
		return nil, fmt.Errorf("read blob: %w", err)
	}

	// If MAC key present, expect a 32-byte tag
	if sc.macKey != nil {
		tag := make([]byte, 32)
		if _, err := io.ReadFull(sc.Conn, tag); err != nil {
			return nil, fmt.Errorf("read hmac: %w", err)
		}
		h := hmac.New(sha256.New, sc.macKey)
		h.Write(blob)
		calc := h.Sum(nil)
		if !hmac.Equal(tag, calc) {
			return nil, errors.New("hmac verification failed")
		}
	}

	if sc.encKey != nil {
		if len(blob) < nonceSize+1 {
			return nil, errors.New("malformed encrypted payload")
		}
		nonce := blob[:nonceSize]
		ct := blob[nonceSize:]
		block, err := aes.NewCipher(sc.encKey)
		if err != nil {
			return nil, fmt.Errorf("aes cipher: %w", err)
		}
		aead, err := cipher.NewGCM(block)
		if err != nil {
			return nil, fmt.Errorf("gcm: %w", err)
		}
		pt, err := aead.Open(nil, nonce, ct, nil)
		if err != nil {
			return nil, fmt.Errorf("decrypt: %w", err)
		}
		return pt, nil
	}
	return blob, nil
}

// Backwards-compatible helpers that try to use SecureConn if provided.
type secureSender interface{ Send([]byte) error }
type secureReceiver interface{ Receive() ([]byte, error) }

// SendData prefers SecureConn if available, else falls back to simple 4B framing (no HMAC/AES).
func SendData(conn net.Conn, data []byte) error {
	if sc, ok := conn.(secureSender); ok {
		return sc.Send(data)
	}
	// Fallback: 4B length + payload
	lenBuf := make([]byte, frameLenSize)
	binary.BigEndian.PutUint32(lenBuf, uint32(len(data)))
	if _, err := conn.Write(lenBuf); err != nil {
		return fmt.Errorf("write len: %w", err)
	}
	if _, err := conn.Write(data); err != nil {
		return fmt.Errorf("write payload: %w", err)
	}
	return nil
}

// ReceiveData prefers SecureConn if available, else reads 4B length + payload.
func ReceiveData(conn net.Conn) ([]byte, error) {
	if sc, ok := conn.(secureReceiver); ok {
		return sc.Receive()
	}
	// Fallback: 4B length + payload
	lenBuf := make([]byte, frameLenSize)
	if _, err := io.ReadFull(conn, lenBuf); err != nil {
		if err == io.EOF {
			return nil, fmt.Errorf("connection closed by peer while reading length: %w", err)
		}
		return nil, fmt.Errorf("read length: %w", err)
	}
	total := binary.BigEndian.Uint32(lenBuf)
	if total == 0 {
		return []byte{}, nil
	}
	payload := make([]byte, total)
	if _, err := io.ReadFull(conn, payload); err != nil {
		return nil, fmt.Errorf("read payload: %w", err)
	}
	return payload, nil
}
