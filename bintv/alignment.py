import numpy as np
import argparse
from typing import List, Tuple, Optional

def sequence_alignment(seq1: bytes, seq2: bytes, gap_penalty: int = -1, 
                       match_score: int = 1, mismatch_penalty: int = -1):
    """
    Perform Needleman-Wunsch sequence alignment on two byte sequences.
    
    Args:
        seq1: First byte sequence
        seq2: Second byte sequence
        gap_penalty: Penalty for inserting a gap
        match_score: Score for matching bytes
        mismatch_penalty: Penalty for mismatched bytes
        
    Returns:
        Tuple containing aligned sequences and alignment score
    """
    # Initialize the scoring matrix
    n, m = len(seq1) + 1, len(seq2) + 1
    score_matrix = np.zeros((n, m), dtype=int)
    
    # Initialize the traceback matrix
    # 0: diagonal (match/mismatch), 1: up (gap in seq2), 2: left (gap in seq1)
    traceback = np.zeros((n, m), dtype=int)
    
    # Initialize first row and column with gap penalties
    for i in range(n):
        score_matrix[i, 0] = i * gap_penalty
    for j in range(m):
        score_matrix[0, j] = j * gap_penalty
    
    # Fill the matrices
    for i in range(1, n):
        for j in range(1, m):
            # Calculate scores for each possible move
            match = score_matrix[i-1, j-1] + (match_score if seq1[i-1] == seq2[j-1] else mismatch_penalty)
            delete = score_matrix[i-1, j] + gap_penalty
            insert = score_matrix[i, j-1] + gap_penalty
            
            # Choose the best score and set the traceback
            if match >= delete and match >= insert:
                score_matrix[i, j] = match
                traceback[i, j] = 0  # diagonal
            elif delete >= insert:
                score_matrix[i, j] = delete
                traceback[i, j] = 1  # up
            else:
                score_matrix[i, j] = insert
                traceback[i, j] = 2  # left
    
    # Traceback to get the aligned sequences
    aligned_seq1 = []
    aligned_seq2 = []
    i, j = n - 1, m - 1
    
    while i > 0 or j > 0:
        if i > 0 and j > 0 and traceback[i, j] == 0:  # diagonal
            aligned_seq1.append(seq1[i-1])
            aligned_seq2.append(seq2[j-1])
            i -= 1
            j -= 1
        elif i > 0 and traceback[i, j] == 1:  # up
            aligned_seq1.append(seq1[i-1])
            aligned_seq2.append(None)  # Gap in seq2
            i -= 1
        else:  # left
            aligned_seq1.append(None)  # Gap in seq1
            aligned_seq2.append(seq2[j-1])
            j -= 1
    
    # Reverse the sequences
    aligned_seq1.reverse()
    aligned_seq2.reverse()
    
    return aligned_seq1, aligned_seq2, score_matrix[n-1, m-1]

def find_continuous_segments(aligned_seq1, aligned_seq2, min_length=4):
    """
    Find continuous segments (no gaps) in the aligned sequences.
    
    Args:
        aligned_seq1: First aligned sequence
        aligned_seq2: Second aligned sequence
        min_length: Minimum length of segments to consider
        
    Returns:
        List of segments with their start positions and lengths
    """
    segments = []
    current_segment_start = None
    current_segment_length = 0
    
    for i in range(len(aligned_seq1)):
        if aligned_seq1[i] is not None and aligned_seq2[i] is not None:
            # Continuous segment (no gaps)
            if current_segment_start is None:
                current_segment_start = i
            current_segment_length += 1
        else:
            # Gap detected, check if current segment is long enough
            if current_segment_length >= min_length:
                segments.append((current_segment_start, current_segment_length))
            current_segment_start = None
            current_segment_length = 0
    
    # Check the last segment
    if current_segment_length >= min_length:
        segments.append((current_segment_start, current_segment_length))
    
    return segments

def detect_integer_values(aligned_seq1, aligned_seq2, sizes=[4, 8]):
    """
    Detect potential integer values in the aligned sequences.
    
    Args:
        aligned_seq1: First aligned sequence
        aligned_seq2: Second aligned sequence
        sizes: List of byte sizes to check for integer values
        
    Returns:
        List of potential integer values with details
    """
    potential_integers = []
    
    # Find continuous segments (no gaps)
    segments = find_continuous_segments(aligned_seq1, aligned_seq2, min_length=min(sizes))
    
    for start_pos, length in segments:
        # Check each possible size
        for size in sizes:
            if length >= size:
                # Check each possible starting position within the segment
                for offset in range(length - size + 1):
                    pos = start_pos + offset
                    
                    # Extract byte sequences
                    seq1_bytes = bytes(aligned_seq1[pos:pos+size])
                    seq2_bytes = bytes(aligned_seq2[pos:pos+size])
                    
                    # Convert to integers (both little and big endian)
                    int1_le = int.from_bytes(seq1_bytes, byteorder='little')
                    int2_le = int.from_bytes(seq2_bytes, byteorder='little')
                    int1_be = int.from_bytes(seq1_bytes, byteorder='big')
                    int2_be = int.from_bytes(seq2_bytes, byteorder='big')
                    
                    # Calculate byte-wise and bit-wise distances
                    byte_distance = sum(b1 != b2 for b1, b2 in zip(seq1_bytes, seq2_bytes))
                    bit_distance_le = bin(int1_le ^ int2_le).count('1')
                    bit_distance_be = bin(int1_be ^ int2_be).count('1')
                    
                    # Calculate similarity scores
                    max_diff = size * 8  # Maximum possible bit difference
                    similarity_le = (max_diff - bit_distance_le) / max_diff * 100
                    similarity_be = (max_diff - bit_distance_be) / max_diff * 100
                    
                    # Check if bytes are similar but not identical
                    if 0 < byte_distance <= size // 2:
                        potential_integers.append({
                            'position': pos,
                            'size': size,
                            'byte_distance': byte_distance,
                            'little_endian': {
                                'value1': int1_le,
                                'value2': int2_le,
                                'bit_distance': bit_distance_le,
                                'similarity': similarity_le
                            },
                            'big_endian': {
                                'value1': int1_be,
                                'value2': int2_be,
                                'bit_distance': bit_distance_be,
                                'similarity': similarity_be
                            }
                        })
    
    return potential_integers

def get_bit_difference_symbol(byte1, byte2):
    """
    Get a symbol representing the bit difference between two bytes.
    
    Args:
        byte1: First byte
        byte2: Second byte
        
    Returns:
        Symbol representing bit difference
    """
    if byte1 == byte2:
        return '||'  # Exact match
    
    bit_diff = bin(byte1 ^ byte2).count('1')
    if bit_diff == 1:
        return '/|'  # 1 bit difference
    elif bit_diff == 2:
        return '~|'  # 2 bit difference
    elif bit_diff <= 4:
        return ':|'  # 3-4 bit difference
    else:
        return '  '  # Significant difference

def visualize_alignment(aligned_seq1, aligned_seq2):
    """
    Visualize the alignment between two byte sequences.
    
    Args:
        aligned_seq1: First aligned sequence
        aligned_seq2: Second aligned sequence
    """
    # Create alignment representation
    seq1_repr = []
    match_repr = []
    seq2_repr = []
    
    for b1, b2 in zip(aligned_seq1, aligned_seq2):
        if b1 is None:
            seq1_repr.append('--')
            match_repr.append('  ')
        else:
            seq1_repr.append(f'{b1:02x}')
        
        if b2 is None:
            seq2_repr.append('--')
            match_repr.append('  ')
        else:
            seq2_repr.append(f'{b2:02x}')
        
        if b1 is not None and b2 is not None:
            match_repr.append(get_bit_difference_symbol(b1, b2))
    
    # Print the alignment with line wrapping (80 chars per line)
    MAX_COLS = 20  # Bytes per line
    print("Sequence Alignment:")
    
    for i in range(0, len(aligned_seq1), MAX_COLS):
        end = min(i + MAX_COLS, len(aligned_seq1))
        print('Seq1: ' + ' '.join(seq1_repr[i:end]))
        print('      ' + ' '.join(match_repr[i:end]))
        print('Seq2: ' + ' '.join(seq2_repr[i:end]))
        print()
    
    print("Match symbols: || = exact match, /| = 1 bit diff, ~| = 2 bit diff, :| = 3-4 bit diff, empty = significant diff")
    print()

def main():
    """Main function to run the sequence alignment."""
    parser = argparse.ArgumentParser(description='Perform sequence alignment on two byte sequences.')
    parser.add_argument('file1', nargs='?', help='First binary file')
    parser.add_argument('file2', nargs='?', help='Second binary file')
    parser.add_argument('--gap', type=int, default=-1, help='Gap penalty (default: -1)')
    parser.add_argument('--match', type=int, default=1, help='Match score (default: 1)')
    parser.add_argument('--mismatch', type=int, default=-1, help='Mismatch penalty (default: -1)')
    parser.add_argument('--int-sizes', type=int, nargs='+', default=[4, 8], 
                        help='Integer sizes to check in bytes (default: 4 8)')
    
    args = parser.parse_args()
    
    # Check if files were provided
    if args.file1 and args.file2:
        # Read binary files
        try:
            with open(args.file1, 'rb') as f1, open(args.file2, 'rb') as f2:
                seq1 = f1.read()
                seq2 = f2.read()
        except FileNotFoundError:
            print("Error: One or both files not found.")
            return
        
        print(f"File 1: {args.file1} ({len(seq1)} bytes)")
        print(f"File 2: {args.file2} ({len(seq2)} bytes)")
    else:
        # Example data
        print("No files provided. Running with example data.")
        
        seq1 = bytes([
            0x01, 0x02, 0x03, 0x04, 0x05, 0xA0, 0xA1, 0xA2, 
            0xFF, 0xFE, 0xFD, 0x00, 0x00, 0x00, 0x00, 0xAA, 
            0xBB, 0xCC, 0xDD, 0x10, 0x20, 0x30, 0x40
        ])
        seq2 = bytes([
            0x01, 0x02, 0x83, 0x04, 0x06, 0xA0, 0xB1, 0xA2, 
            0xFF, 0xEE, 0xFD, 0x00, 0x01, 0x00, 0x00, 0xAA, 
            0xCB, 0xCC, 0xDD, 0x11, 0x21, 0x31, 0x41
        ])
        
        print(f"Seq1 ({len(seq1)} bytes): {' '.join(f'{b:02x}' for b in seq1)}")
        print(f"Seq2 ({len(seq2)} bytes): {' '.join(f'{b:02x}' for b in seq2)}")
    
    print()
    
    # Perform sequence alignment
    aligned_seq1, aligned_seq2, score = sequence_alignment(
        seq1, seq2, args.gap, args.match, args.mismatch
    )
    
    # Visualize the alignment
    visualize_alignment(aligned_seq1, aligned_seq2)
    
    # Detect potential integer values
    potential_integers = detect_integer_values(aligned_seq1, aligned_seq2, args.int_sizes)
    
    # Display results
    print(f"Alignment score: {score}")
    print()
    
    if potential_integers:
        print(f"Found {len(potential_integers)} potential integer values:")
        for idx, p in enumerate(potential_integers, 1):
            print(f"#{idx} - Position: {p['position']}, Size: {p['size']} bytes, Byte distance: {p['byte_distance']}")
            
            # Little endian
            le = p['little_endian']
            print(f"  Little Endian:")
            print(f"    Value 1: {le['value1']} (0x{le['value1']:x})")
            print(f"    Value 2: {le['value2']} (0x{le['value2']:x})")
            print(f"    Bit distance: {le['bit_distance']} bits")
            print(f"    Similarity: {le['similarity']:.2f}%")
            
            # Big endian
            be = p['big_endian']
            print(f"  Big Endian:")
            print(f"    Value 1: {be['value1']} (0x{be['value1']:x})")
            print(f"    Value 2: {be['value2']} (0x{be['value2']:x})")
            print(f"    Bit distance: {be['bit_distance']} bits")
            print(f"    Similarity: {be['similarity']:.2f}%")
            print()
    else:
        print("No potential integer values detected.")

if __name__ == "__main__":
    main()
