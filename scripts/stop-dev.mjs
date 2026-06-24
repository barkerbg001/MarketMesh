import { execSync } from 'node:child_process'

const ports = [8000, 5173]
const projectRoot = process.cwd().replace(/\\/g, '\\\\')

function getPidsOnPortWindows(port) {
  let output = ''
  try {
    output = execSync(`netstat -ano | findstr ":${port}"`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    })
  } catch {
    return []
  }

  const pids = new Set()
  for (const line of output.split('\n')) {
    if (!line.includes('LISTENING')) continue
    const pid = line.trim().split(/\s+/).at(-1)
    if (pid && pid !== '0') pids.add(pid)
  }
  return [...pids]
}

function getPidsOnPortUnix(port) {
  try {
    const output = execSync(`lsof -tiTCP:${port} -sTCP:LISTEN`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    })
    return output
      .split('\n')
      .map((pid) => pid.trim())
      .filter(Boolean)
  } catch {
    return []
  }
}

function getProjectUvicornPidsWindows() {
  try {
    const output = execSync(
      `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name='python.exe'\\" | Where-Object { $_.CommandLine -like '*uvicorn*' -and $_.CommandLine -like '*${projectRoot}*' } | Select-Object -ExpandProperty ProcessId"`,
      { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] },
    )
    return output
      .split('\n')
      .map((pid) => pid.trim())
      .filter(Boolean)
  } catch {
    return []
  }
}

function getProjectVitePidsWindows() {
  try {
    const output = execSync(
      `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name='node.exe'\\" | Where-Object { $_.CommandLine -like '*vite*' -and $_.CommandLine -like '*${projectRoot}*' } | Select-Object -ExpandProperty ProcessId"`,
      { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] },
    )
    return output
      .split('\n')
      .map((pid) => pid.trim())
      .filter(Boolean)
  } catch {
    return []
  }
}

function killPid(pid) {
  if (process.platform === 'win32') {
    execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' })
    return
  }
  execSync(`kill -9 ${pid}`, { stdio: 'ignore' })
}

const killed = new Set()

function stopPid(pid, reason) {
  if (!pid || killed.has(pid)) return
  try {
    killPid(pid)
    killed.add(pid)
    console.log(`Stopped PID ${pid} (${reason})`)
  } catch {
    console.warn(`Could not stop PID ${pid} (${reason})`)
  }
}

if (process.platform === 'win32') {
  for (const pid of getProjectUvicornPidsWindows()) {
    stopPid(pid, 'uvicorn')
  }
  for (const pid of getProjectVitePidsWindows()) {
    stopPid(pid, 'vite')
  }
}

for (const port of ports) {
  const pids =
    process.platform === 'win32'
      ? getPidsOnPortWindows(port)
      : getPidsOnPortUnix(port)

  for (const pid of pids) {
    stopPid(pid, `port ${port}`)
  }
}

if (killed.size === 0) {
  console.log('No dev servers found on ports 8000 or 5173.')
} else {
  console.log(`Freed ${killed.size} process(es). You can run npm run dev now.`)
}
