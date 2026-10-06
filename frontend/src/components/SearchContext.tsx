import { createContext, useContext, useState, type ReactNode } from 'react'
import type { SearchResults } from '../api/chat'

// Search results the chatbot found. The chat widget sets them; the Products page shows them.
type SearchState = {
  search: SearchResults | null
  setSearch: (s: SearchResults | null) => void
}

const SearchContext = createContext<SearchState | null>(null)

export function SearchProvider({ children }: { children: ReactNode }) {
  const [search, setSearch] = useState<SearchResults | null>(null)
  return <SearchContext.Provider value={{ search, setSearch }}>{children}</SearchContext.Provider>
}

export function useSearch() {
  const ctx = useContext(SearchContext)
  if (!ctx) throw new Error('useSearch must be used inside <SearchProvider>')
  return ctx
}
