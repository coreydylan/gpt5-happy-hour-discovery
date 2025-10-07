import crypto from 'crypto';

const ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz';
const SIZE = 12;

export function nanoid(): string {
  const bytes = crypto.randomBytes(SIZE);
  let id = '';
  for (let i = 0; i < SIZE; i += 1) {
    id += ALPHABET[bytes[i] % ALPHABET.length];
  }
  return id;
}
