#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { Transform } from 'node:stream'

/**
 * Parses CLI arguments in the format --key=value or --flag
 */
function parseArgs() {
  const args = {}
  for (const arg of process.argv.slice(2)) {
    if (arg.startsWith('--')) {
      const [key, ...values] = arg.slice(2).split('=')
      args[key] = values.join('=') || true
    }
  }
  return args
}

const args = parseArgs()

// Load .env directly from jf_dsm_upload_service/.env
const serviceEnvPath = path.resolve(path.dirname(new URL(import.meta.url).pathname), '.env')
if (fs.existsSync(serviceEnvPath)) {
  try {
    process.loadEnvFile(serviceEnvPath)
  } catch (_) {}
}

// Fallback to project-level .env or .env.local
for (const envFile of ['.env', '.env.local', '../.env', '../../.env']) {
  if (fs.existsSync(envFile)) {
    try {
      process.loadEnvFile(envFile)
      break
    } catch (_) {}
  }
}

// Bypass TLS certificate mismatch if --insecure flag or ALLOW_INSECURE_TLS is set
if (args.insecure || process.env.ALLOW_INSECURE_TLS !== 'false') {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'
}

// Configuration defaults for kj_job_finder
const DEPLOY_API_URL = args.url || process.env.DEPLOY_API_URL || 'https://fastbyte.twilightparadox.com/upload'
const DEPLOY_SECRET_TOKEN = args.token || process.env.DEPLOY_SECRET_TOKEN
const TARGET_SUBFOLDER = args.subfolder !== undefined ? args.subfolder : (process.env.TARGET_SUBFOLDER || 'kj_job_finder/x_deployment')

if (!DEPLOY_SECRET_TOKEN) {
  console.error('[ ❌ ] Error: DEPLOY_SECRET_TOKEN is not set.')
  console.error('      Provide it via --token=... or set DEPLOY_SECRET_TOKEN in .env')
  process.exit(1)
}

/**
 * Uploads a single file to DSM
 */
async function uploadFile(localFilePath) {
  const resolvedPath = path.resolve(localFilePath)
  if (!fs.existsSync(resolvedPath)) {
    console.error(`[ ❌ ] Error: Local file not found at: ${resolvedPath}`)
    return false
  }

  const stats = fs.statSync(resolvedPath)
  const totalBytes = stats.size
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(2)
  const effectiveFilename = path.basename(resolvedPath)

  const targetUrl = new URL(DEPLOY_API_URL)
  if (TARGET_SUBFOLDER) {
    targetUrl.searchParams.set('subfolder', TARGET_SUBFOLDER)
  }
  targetUrl.searchParams.set('filename', effectiveFilename)

  console.log(`\n======================================================================`)
  console.log(`[ ℹ️ 📦 ] Uploading: ${effectiveFilename} (${totalMB} MB)`)
  console.log(`[ ℹ️ 📁 ] Target: /volume1/api_files_receiver/${TARGET_SUBFOLDER}/${effectiveFilename}`)
  console.log(`======================================================================`)

  let uploadedBytes = 0
  let lastPercent = -1

  const progressStream = new Transform({
    transform(chunk, encoding, callback) {
      uploadedBytes += chunk.length
      const percent = Math.round((uploadedBytes / totalBytes) * 100)
      if (percent !== lastPercent) {
        lastPercent = percent
        const currentMB = (uploadedBytes / (1024 * 1024)).toFixed(2)
        process.stdout.write(`\r[ ⏳ ] Progress: ${percent}% (${currentMB} MB / ${totalMB} MB)`)
      }
      callback(null, chunk)
    },
  })

  const fileReadStream = fs.createReadStream(resolvedPath).pipe(progressStream)
  const startTime = Date.now()

  try {
    const response = await fetch(targetUrl.toString(), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${DEPLOY_SECRET_TOKEN}`,
        'Content-Type': 'application/octet-stream',
        'Content-Length': totalBytes.toString(),
        'X-Filename': encodeURIComponent(effectiveFilename),
        ...(TARGET_SUBFOLDER ? { 'X-Subfolder': TARGET_SUBFOLDER } : {}),
      },
      body: fileReadStream,
      duplex: 'half',
    })

    process.stdout.write('\n[ ℹ️ ⚙️ ] Processing and loading into Container Manager on Synology DSM...\n')

    const result = await response.json()

    if (!response.ok || !result.success) {
      console.error('[ ❌ ] Upload rejected by server:', JSON.stringify(result, null, 2))
      return false
    }

    const durationSec = ((Date.now() - startTime) / 1000).toFixed(2)
    console.log(`[ 🎉 ✅ ] ${effectiveFilename} received and processed in ${durationSec}s!`)
    console.log(`Saved In   : /volume1/api_files_receiver/${result.file?.savedPath || 'N/A'}`)
    if (result.hook?.livePath) {
      console.log(`Moved To   : ${result.hook.livePath}`)
    }
    const dockerInfo = result.hook?.redeployOutput || result.hook?.loadOutput
    if (dockerInfo) {
      console.log(`Docker Info: ${dockerInfo}`)
    }
    return true
  } catch (err) {
    console.error('\n[ ❌ ] Network/Upload error:', err.message)
    return false
  }
}

// -----------------------------------------------------------------------------
// Execution flow: single file or all files in dsm_deploy/docker_images
// -----------------------------------------------------------------------------
async function main() {
  if (args.file) {
    const success = await uploadFile(args.file)
    process.exit(success ? 0 : 1)
  }

  // Default: Upload all .tar images inside dsm_deploy/docker_images/
  const scriptDir = path.dirname(new URL(import.meta.url).pathname)
  const imagesDir = path.resolve(scriptDir, '../docker_images')

  if (!fs.existsSync(imagesDir)) {
    console.error(`[ ❌ ] Images directory not found: ${imagesDir}`)
    console.error('      Please run "npm run docker:save-tar" first or provide --file=<path>')
    process.exit(1)
  }

  const tarFiles = fs.readdirSync(imagesDir).filter((f) => f.endsWith('.tar'))
  if (tarFiles.length === 0) {
    console.error(`[ ❌ ] No .tar files found in: ${imagesDir}`)
    process.exit(1)
  }

  console.log(`🚀 Found ${tarFiles.length} Docker image archives to deploy to Synology DSM:`)
  for (const f of tarFiles) {
    console.log(`  - ${f}`)
  }

  let failedCount = 0
  for (const f of tarFiles) {
    const fullPath = path.join(imagesDir, f)
    const ok = await uploadFile(fullPath)
    if (!ok) failedCount++
  }

  console.log('\n======================================================================')
  if (failedCount === 0) {
    console.log('🎉 ALL IMAGES SUCCESSFULLY DEPLOYED AND LOADED ON SYNOLOGY DSM!')
  } else {
    console.error(`⚠️ Finished with ${failedCount} failure(s).`)
  }
  console.log('======================================================================\n')
  process.exit(failedCount > 0 ? 1 : 0)
}

main()
