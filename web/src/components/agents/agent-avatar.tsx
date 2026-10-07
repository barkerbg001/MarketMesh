import { useMemo } from 'react'

import { agentAvatarUri } from '@/lib/avatars'
import { cn } from '@/lib/utils'
import type { Agent } from '@/types/api'

const SIZES = { sm: 'size-6', md: 'size-8', lg: 'size-12' } as const

export function AgentAvatar({
  agent,
  size = 'md',
  className,
}: {
  agent: Pick<Agent, 'name' | 'avatar_seed' | 'avatar_background'>
  size?: keyof typeof SIZES
  className?: string
}) {
  const src = useMemo(() => agentAvatarUri(agent.avatar_seed, agent.avatar_background), [agent])
  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      className={cn('shrink-0 rounded-full bg-muted', SIZES[size], className)}
      width={48}
      height={48}
    />
  )
}
