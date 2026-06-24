import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const apiDir = join(process.cwd(), 'api')
const venvDir = join(apiDir, '.venv')
const venvPython =
  process.platform === 'win32'
    ? join(venvDir, 'Scripts', 'python.exe')
    : join(venvDir, 'bin', 'python')
const venvPip =
  process.platform === 'win32'
    ? join(venvDir, 'Scripts', 'pip.exe')
    : join(venvDir, 'bin', 'pip')

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    ...options,
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

if (!existsSync(venvPython)) {
  console.log('Creating API virtual environment...')
  run('python', ['-m', 'venv', '.venv'], { cwd: apiDir })
}

console.log('Installing API dependencies...')
run(venvPip, ['install', '-r', 'requirements.txt'], { cwd: apiDir })

console.log('API setup complete.')
