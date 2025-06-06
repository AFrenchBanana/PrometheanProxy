package session

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

const (
	// ChunkSize defines the size of each data chunk for transmission.
	ChunkSize = 4096
)

// SendData sends a byte slice over a connection using a custom header protocol.
// It first sends an 8-byte header containing the total data length and chunk size,
// followed by the data payload itself, sent in chunks.
// This function is a direct Go equivalent of your Python `send_data` function.
//
// Parameters:
//   - conn: The network connection (e.g., *tls.Conn) to write data to.
//   - data: The byte slice to be sent.
//
// Returns:
//   - An error if any write operation fails.
func SendData(conn net.Conn, data []byte) error {
	// --- Step 1: Prepare and send the header ---
	// The header consists of two 32-bit unsigned integers in Big Endian format.
	// Big Endian is network byte order, matching '!' in Python's struct.pack.
	header := make([]byte, 8)
	totalLength := uint32(len(data))
	chunkSize := uint32(ChunkSize)

	binary.BigEndian.PutUint32(header[0:4], totalLength)
	binary.BigEndian.PutUint32(header[4:8], chunkSize)

	// Send the 8-byte header.
	if _, err := conn.Write(header); err != nil {
		return fmt.Errorf("failed to send header: %w", err)
	}

	// --- Step 2: Send the data payload in chunks ---
	bytesSent := 0
	for bytesSent < len(data) {
		end := bytesSent + ChunkSize
		if end > len(data) {
			end = len(data)
		}

		chunk := data[bytesSent:end]
		n, err := conn.Write(chunk)
		if err != nil {
			return fmt.Errorf("failed to send data chunk: %w", err)
		}
		bytesSent += n
	}

	return nil
}

// ReceiveData reads data from a connection that uses the custom header protocol.
// It first reads an 8-byte header to determine the total data length and chunk size,
// then reads the specified amount of data from the connection.
// This function is a direct Go equivalent of your Python `receive_data` function.
//
// Parameters:
//   - conn: The network connection (e.g., *tls.Conn) to read data from.
//
// Returns:
//   - A byte slice containing the received data.
//   - An error if any read operation fails or the header is malformed.
func ReceiveData(conn net.Conn) ([]byte, error) {
	// --- Step 1: Read and unpack the header ---
	header := make([]byte, 8)
	// io.ReadFull ensures that we read exactly 8 bytes for the header.
	// This prevents partial reads and simplifies error handling.
	if _, err := io.ReadFull(conn, header); err != nil {
		if err == io.EOF {
			return nil, fmt.Errorf("connection closed by peer while reading header: %w", err)
		}
		return nil, fmt.Errorf("failed to read header: %w", err)
	}

	totalLength := binary.BigEndian.Uint32(header[0:4])
	// The chunkSize from the header is noted but our read logic doesn't
	// strictly need it, as we read until totalLength is satisfied.

	// --- Step 2: Read the data payload ---
	// Make a buffer of the exact size needed to hold the incoming data.
	if totalLength == 0 {
		return []byte{}, nil // No data to receive
	}

	receivedData := make([]byte, totalLength)
	// Use io.ReadFull again to ensure we read the entire payload.
	if _, err := io.ReadFull(conn, receivedData); err != nil {
		return nil, fmt.Errorf("failed to read full data payload: %w", err)
	}

	// Unlike Python, Go doesn't guess the encoding. We return the raw bytes.
	// The calling function is responsible for interpreting the data (e.g., decoding as UTF-8).
	return receivedData, nil
}
