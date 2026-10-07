import { useSyncExternalStore } from 'react'

export type Route =
  | { view: 'chat'; conversationId: string | null }
  | { view: 'search' }
  | { view: 'settings'; section: string | null }

const UUID = /^[0-9a-f-]{36}$/i

export function parseRoute(hash: string): Route {
  const [view, param] = hash.replace(/^#\/?/, '').split('/')
  if (view === 'search') return { view: 'search' }
  if (view === 'settings') return { view: 'settings', section: param || null }
  return { view: 'chat', conversationId: param && UUID.test(param) ? param : null }
}

export function routeHref(route: Route) {
  switch (route.view) {
    case 'search':
      return '#/search'
    case 'settings':
      return route.section ? `#/settings/${route.section}` : '#/settings'
    default:
      return route.conversationId ? `#/chat/${route.conversationId}` : '#/chat'
  }
}

export function navigate(route: Route) {
  window.location.hash = routeHref(route)
}

function subscribe(onChange: () => void) {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

const getHash = () => window.location.hash

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, getHash, () => '')
  return parseRoute(hash)
}
