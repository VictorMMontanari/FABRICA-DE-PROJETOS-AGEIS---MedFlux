import { useState } from 'react'
import type { UserProfile } from '../services/api'

type UserAvatarProps = {
  user?: UserProfile
  className?: string
}

export function UserAvatar({ user, className = 'profile-chip__avatar' }: UserAvatarProps) {
  // A URL da foto é pré-assinada e expira: se a imagem falhar, mostra as iniciais.
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const url = user?.avatar_url

  if (url && url !== failedUrl) {
    return (
      <div className={className}>
        <img src={url} alt={user?.name ?? 'Foto de perfil'} onError={() => setFailedUrl(url)} />
      </div>
    )
  }

  return <div className={className}>{user?.avatarInitials ?? '?'}</div>
}
