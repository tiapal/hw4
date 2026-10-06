import type { Product } from './products'

export type ChatTurn = { role: 'user' | 'assistant'; content: string }
export type SearchResults = { query: string; total: number; products: Product[] }
export type ChatReply = { message: string; products: Product[]; search: SearchResults | null }
export type PageContext = { path: string; product_id: string | null }
export type SavedMessage = ChatTurn & { products: Product[]; created_at: string }

const HISTORY_TURNS = 10 // how much of the conversation a guest's message carries along

// `history` is only used for guests. For logged-in shoppers the server loads their saved chat itself.
export async function sendChat(message: string, history: ChatTurn[], page: PageContext): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history: history.slice(-HISTORY_TURNS), page }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : 'Something went wrong. Please try again.')
  }
  return data as ChatReply
}

// The logged-in shopper's saved messages (empty for guests).
export async function fetchChatHistory(): Promise<SavedMessage[]> {
  const res = await fetch('/api/chat/history', { cache: 'no-store' })
  if (!res.ok) return []
  return (await res.json()).messages as SavedMessage[]
}
