import net from 'node:net'
import { execSync } from 'node:child_process'

const ports = [8000, 5173]

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => resolve(false))
    server.once('listening', () => server.close(() => resolve(true)))
    server.listen(port, '127.0.0.1')
  })
}

function listPortOwners(port) {
  if (process.platform === 'win32') {
    try {
      return execSync(`netstat -ano | findstr ":${port}"`, { encoding: 'utf8' }).trim()
    } catch {
      return ''
    }
  }

  try {
    return execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN`, { encoding: 'utf8' }).trim()
  } catch {
    return ''
  }
}

const blocked = []

for (const port of ports) {
  if (!(await isPortFree(port))) {
    blocked.push(port)
  }
}

if (blocked.length > 0) {
  console.error(`Dev ports already in use: ${blocked.join(', ')}`)
  for (const port of blocked) {
    const owners = listPortOwners(port)
    if (owners) {
      console.error(`\nPort ${port}:\n${owners}`)
    }
  }
  console.error(
    '\nStop the old dev servers first, then run npm run dev again.',
  )
  if (process.platform === 'win32') {
    console.error('Example: taskkill /F /PID <pid>')
  }
  process.exit(1)
}
