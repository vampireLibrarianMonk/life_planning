// Auth is carried by an httpOnly cookie now, so every same-origin request must
// send credentials. We patch window.fetch once to (a) default credentials to
// 'include' and (b) surface a friendly toast on 403 (readonly/stale session).
if (typeof window !== 'undefined' && !window.__api403Patched) {
  window.__api403Patched = true
  const origFetch = window.fetch.bind(window)
  window.fetch = async (input, init = {}) => {
    const merged = { credentials: 'include', ...init }
    const res = await origFetch(input, merged)
    try {
      const url = typeof input === 'string' ? input : input?.url || ''
      if (res.status === 403 && url.includes('/api/')) {
        window.dispatchEvent(new CustomEvent('api-forbidden'))
      }
    } catch {
      /* never let the interceptor break a request */
    }
    return res
  }
}

const headers = () => ({
  'Content-Type': 'application/json',
})

export async function fetchProfiles() {
  const res = await fetch('/api/profiles/', { headers: headers() })
  return res.json()
}

export async function createProfile(name, dateOfBirth) {
  const res = await fetch('/api/profiles/', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ name, date_of_birth: dateOfBirth || null }),
  })
  return res.json()
}

export async function reseedProfile(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/reseed`, {
    method: 'POST',
    headers: headers(),
  })
  return res.json()
}

export async function fetchProfile(id) {
  const res = await fetch(`/api/profiles/${id}`, { headers: headers() })
  return res.json()
}

export async function fetchEntries(profileId, pillar = null) {
  const params = pillar ? `?pillar=${pillar}` : ''
  const res = await fetch(`/api/profiles/${profileId}/entries/${params}`, { headers: headers() })
  return res.json()
}

export async function fetchChildren(profileId, entryId) {
  const res = await fetch(`/api/profiles/${profileId}/entries/${entryId}/children`, { headers: headers() })
  return res.json()
}

export async function createEntry(profileId, entry) {
  const res = await fetch(`/api/profiles/${profileId}/entries/`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(entry),
  })
  return res.json()
}

export async function updateEntry(profileId, entryId, updates) {
  const res = await fetch(`/api/profiles/${profileId}/entries/${entryId}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify(updates),
  })
  return res.json()
}

export async function deleteEntry(profileId, entryId) {
  await fetch(`/api/profiles/${profileId}/entries/${entryId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

// Economy
export async function fetchBehavior(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/behavior`, { headers: headers() })
  return res.json()
}

export async function createBehavior(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/behavior`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateBehavior(profileId, scoreId, data) {
  const res = await fetch(`/api/profiles/${profileId}/behavior/${scoreId}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function fetchEligibility(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/eligibility`, { headers: headers() })
  return res.json()
}

export async function fetchBounties(profileId, pillar = null) {
  const params = pillar ? `?pillar=${pillar}` : ''
  const res = await fetch(`/api/profiles/${profileId}/bounties${params}`, { headers: headers() })
  return res.json()
}

export async function createBounty(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/bounties`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateBounty(profileId, bountyId, data) {
  const res = await fetch(`/api/profiles/${profileId}/bounties/${bountyId}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteBounty(profileId, bountyId) {
  await fetch(`/api/profiles/${profileId}/bounties/${bountyId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

export async function fetchEarnings(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/earnings`, { headers: headers() })
  return res.json()
}

// Wishlist
export async function fetchWishlist(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/wishlist`, { headers: headers() })
  return res.json()
}

export async function createWishlistItem(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/wishlist`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateWishlistItem(profileId, itemId, data) {
  const res = await fetch(`/api/profiles/${profileId}/wishlist/${itemId}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteWishlistItem(profileId, itemId) {
  await fetch(`/api/profiles/${profileId}/wishlist/${itemId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

// Profile Avatar
export async function uploadAvatar(profileId, originalFile, croppedBlob) {
  const formData = new FormData()
  formData.append('original', originalFile)
  formData.append('cropped', croppedBlob, 'avatar.png')
  const res = await fetch(`/api/profiles/${profileId}/avatar`, {
    method: 'POST',
    body: formData,
  })
  return res.json()
}

// Behavior Incidents
export async function fetchIncidents(profileId, days = 30) {
  const res = await fetch(`/api/profiles/${profileId}/incidents?days=${days}`, { headers: headers() })
  return res.json()
}

export async function createIncident(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/incidents`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteIncident(profileId, incidentId) {
  await fetch(`/api/profiles/${profileId}/incidents/${incidentId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

// Event Attachments
export async function uploadAttachments(profileId, entryId, files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const res = await fetch(`/api/profiles/${profileId}/entries/${entryId}/attachments/`, {
    method: 'POST',
    body: formData,
  })
  return res.json()
}

export async function fetchAttachments(profileId, entryId) {
  const res = await fetch(`/api/profiles/${profileId}/entries/${entryId}/attachments/`, { headers: headers() })
  return res.json()
}

export async function deleteAttachment(profileId, entryId, attachmentId) {
  await fetch(`/api/profiles/${profileId}/entries/${entryId}/attachments/${attachmentId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

export async function fetchPillarGuide(pillar) {
  const res = await fetch(`/api/docs/${pillar}`, { headers: headers() })
  if (!res.ok) return null
  return res.json()
}

export async function fetchResearchTopics(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/research-topics`, { headers: headers() })
  if (!res.ok) return {}
  return res.json()
}

export async function fetchPrograms(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/programs`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function fetchDiscernmentCategories(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/discernment/categories`, { headers: headers() })
  if (!res.ok) return {}
  return res.json()
}

export async function fetchDiscernmentEntries(profileId, category = null) {
  const params = category ? `?category=${category}` : ''
  const res = await fetch(`/api/profiles/${profileId}/discernment/${params}`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function createDiscernmentEntry(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/discernment/`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteDiscernmentEntry(profileId, entryId) {
  await fetch(`/api/profiles/${profileId}/discernment/${entryId}`, { method: 'DELETE', headers: headers() })
}

export async function fetchBountyLogs(profileId, bountyId) {
  const res = await fetch(`/api/profiles/${profileId}/bounties/${bountyId}/logs`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function createBountyLog(profileId, bountyId, data) {
  const res = await fetch(`/api/profiles/${profileId}/bounties/${bountyId}/logs`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteBountyLog(profileId, bountyId, logId) {
  await fetch(`/api/profiles/${profileId}/bounties/${bountyId}/logs/${logId}`, { method: 'DELETE', headers: headers() })
}

export async function fetchDiscernments(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/discernments/`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function createDiscernment(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/discernments/`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function updateDiscernment(profileId, id, data) {
  const res = await fetch(`/api/profiles/${profileId}/discernments/${id}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteDiscernment(profileId, id) {
  await fetch(`/api/profiles/${profileId}/discernments/${id}`, { method: 'DELETE', headers: headers() })
}


// --- Funds ---

export async function fetchFunds(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/funds/`, { headers: headers() })
  return res.json()
}

export async function createFund(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/funds/`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteFund(profileId, fundId) {
  await fetch(`/api/profiles/${profileId}/funds/${fundId}`, { method: 'DELETE', headers: headers() })
}

export async function fetchFundTransactions(profileId, fundId) {
  const res = await fetch(`/api/profiles/${profileId}/funds/${fundId}/transactions`, { headers: headers() })
  return res.json()
}

export async function createFundTransaction(profileId, fundId, data) {
  const res = await fetch(`/api/profiles/${profileId}/funds/${fundId}/transactions`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteFundTransaction(profileId, fundId, txnId) {
  await fetch(`/api/profiles/${profileId}/funds/${fundId}/transactions/${txnId}`, { method: 'DELETE', headers: headers() })
}

// --- Lesson Plans ---

export async function fetchLessons(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/lessons/`, { headers: headers() })
  return res.json()
}

export async function createLesson(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/lessons/`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function updateLesson(profileId, lessonId, data) {
  const res = await fetch(`/api/profiles/${profileId}/lessons/${lessonId}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteLesson(profileId, lessonId) {
  await fetch(`/api/profiles/${profileId}/lessons/${lessonId}`, { method: 'DELETE', headers: headers() })
}

export async function createLessonResponse(profileId, lessonId, data) {
  const res = await fetch(`/api/profiles/${profileId}/lessons/${lessonId}/responses`, { method: 'POST', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

export async function deleteLessonResponse(profileId, lessonId, responseId) {
  await fetch(`/api/profiles/${profileId}/lessons/${lessonId}/responses/${responseId}`, { method: 'DELETE', headers: headers() })
}


// --- Budget ---

export async function fetchBudget(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/budget`, { headers: headers() })
  return res.json()
}

export async function updateBudget(profileId, data) {
  const res = await fetch(`/api/profiles/${profileId}/budget`, { method: 'PATCH', headers: headers(), body: JSON.stringify(data) })
  return res.json()
}

// --- Archive / restore / delete -------------------------------------------

/**
 * Download a full .zip archive of a profile and return the one-time archive
 * token from the response header (needed to authorize a delete). Admin + the
 * owning child may archive.
 */
export async function archiveProfile(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/archive`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Archive failed')
  const token = res.headers.get('X-Archive-Token')
  const blob = await res.blob()
  // Trigger a browser download.
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `life-plan-profile-${profileId}-archive.zip`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return token
}

/** Full clean delete (admin only) — requires a fresh archive token. */
export async function deleteProfile(profileId, archiveToken) {
  // Send the token as a header (keeps it out of URLs/access logs).
  const res = await fetch(`/api/profiles/${profileId}`, {
    method: 'DELETE',
    headers: { 'X-Archive-Token': archiveToken },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'Delete failed')
  }
  return res.json().catch(() => ({}))
}

/** Full restore (admin only) from a previously-downloaded archive .zip. */
export async function restoreProfile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/api/profiles/restore', {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'Restore failed')
  }
  return res.json()
}

// --- Child Development section -------------------------------------------

export async function fetchCDOverview(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/child-development/`, { headers: headers() })
  return res.json()
}

export async function fetchCDAgeGroup(profileId, ageBand) {
  const res = await fetch(`/api/profiles/${profileId}/child-development/${ageBand}`, { headers: headers() })
  return res.json()
}

export async function seedCDAgeGroup(profileId, ageBand) {
  const res = await fetch(`/api/profiles/${profileId}/child-development/${ageBand}/seed`, {
    method: 'POST', headers: headers(),
  })
  return res.json()
}

export async function deactivateCDAgeGroup(profileId, ageBand) {
  await fetch(`/api/profiles/${profileId}/child-development/${ageBand}`, {
    method: 'DELETE', headers: headers(),
  })
}

export async function fetchCDWorries(profileId, ageBand) {
  const res = await fetch(`/api/profiles/${profileId}/child-development/${ageBand}/worries`, { headers: headers() })
  if (!res.ok) return { content: '' }
  return res.json()
}

export async function saveCDWorries(profileId, ageBand, content) {
  const res = await fetch(`/api/profiles/${profileId}/child-development/${ageBand}/worries`, {
    method: 'PUT', headers: headers(), body: JSON.stringify({ content }),
  })
  return res.json()
}

// --- Gallery (canonical child media) -----------------------------------------

export async function fetchGallery(profileId, { ageBand, mediaType, objectiveId } = {}) {
  const params = new URLSearchParams()
  if (ageBand) params.set('age_band', ageBand)
  if (mediaType) params.set('media_type', mediaType)
  if (objectiveId != null) params.set('objective_id', objectiveId)
  const qs = params.toString() ? `?${params}` : ''
  const res = await fetch(`/api/profiles/${profileId}/gallery/${qs}`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function uploadGalleryMedia(profileId, files) {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  const res = await fetch(`/api/profiles/${profileId}/gallery/`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    let detail = `Upload failed (HTTP ${res.status})`
    if (res.status === 413) detail = 'That file is too large to upload here.'
    else {
      try {
        const body = await res.json()
        if (body && body.detail) detail = typeof body.detail === 'string' ? body.detail : detail
      } catch {
        /* non-JSON error body */
      }
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res.json()
}

// Files at/above this size use the direct-to-storage flow (initiate -> PUT ->
// finalize) so they bypass the app's request-body size cap. Must stay well
// under that 50MB cap for the buffered path. Phone videos routinely exceed it.
export const DIRECT_UPLOAD_THRESHOLD = 20 * 1024 * 1024 // 20 MB

/**
 * Upload a single file via the direct-to-storage flow. Returns the finalized
 * media object. Used for large videos; small files use uploadGalleryMedia.
 */
export async function directUploadGalleryMedia(profileId, file, { observation, ageBand } = {}) {
  // 1. initiate — reserve a pending media row + get an upload URL
  const initRes = await fetch(`/api/profiles/${profileId}/gallery/uploads/initiate`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
    }),
  })
  if (!initRes.ok) {
    let detail = `Could not start upload (HTTP ${initRes.status})`
    try {
      const b = await initRes.json()
      if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const { media_id, upload_url } = await initRes.json()

  // 2. PUT the bytes straight to storage (S3 presigned URL, or local receiver).
  // credentials only for the same-origin local receiver; a presigned S3 URL
  // must NOT carry our cookie, so omit credentials for cross-origin targets.
  const sameOrigin = upload_url.startsWith('/')
  const putRes = await fetch(upload_url, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    credentials: sameOrigin ? 'include' : 'omit',
  })
  if (!putRes.ok) throw new Error(`Upload transfer failed (HTTP ${putRes.status})`)

  // 3. finalize — server verifies the object landed, flips to ready
  const finRes = await fetch(`/api/profiles/${profileId}/gallery/uploads/${media_id}/finalize`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ observation: observation ?? null, age_band: ageBand ?? null }),
  })
  if (!finRes.ok) {
    let detail = `Could not finalize upload (HTTP ${finRes.status})`
    try {
      const b = await finRes.json()
      if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return finRes.json()
}

/** Upload any files, auto-selecting buffered vs. direct per file size. */
export async function smartUploadGalleryMedia(profileId, files, opts = {}) {
  const small = []
  const results = []
  for (const f of files) {
    if (f.size >= DIRECT_UPLOAD_THRESHOLD) {
      results.push(await directUploadGalleryMedia(profileId, f, opts))
    } else {
      small.push(f)
    }
  }
  if (small.length) {
    const created = await uploadGalleryMedia(profileId, small)
    if (Array.isArray(created)) results.push(...created)
  }
  return results
}

export async function updateGalleryMedia(profileId, mediaId, updates) {
  const res = await fetch(`/api/profiles/${profileId}/gallery/${mediaId}`, {
    method: 'PATCH', headers: headers(), body: JSON.stringify(updates),
  })
  return res.json()
}

export async function deleteGalleryMedia(profileId, mediaId) {
  await fetch(`/api/profiles/${profileId}/gallery/${mediaId}`, { method: 'DELETE' })
}

export async function linkGalleryObjective(profileId, mediaId, objectiveId) {
  const res = await fetch(`/api/profiles/${profileId}/gallery/${mediaId}/objective-links`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ objective_id: objectiveId }),
  })
  return res.json()
}

export async function unlinkGalleryObjective(profileId, mediaId, objectiveId) {
  await fetch(`/api/profiles/${profileId}/gallery/${mediaId}/objective-links/${objectiveId}`, {
    method: 'DELETE',
  })
}

// --- Contacts & groups (v6 Pass 4) -------------------------------------------

export async function fetchContacts(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/contacts/`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function fetchRelationshipSubtypes(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/contacts/relationship-subtypes`, { headers: headers() })
  if (!res.ok) return {}
  return res.json()
}

export async function createContact(profileId, contact) {
  const res = await fetch(`/api/profiles/${profileId}/contacts/`, {
    method: 'POST', headers: headers(), body: JSON.stringify(contact),
  })
  if (!res.ok) {
    let detail = `Could not save contact (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function updateContact(profileId, contactId, updates) {
  const res = await fetch(`/api/profiles/${profileId}/contacts/${contactId}`, {
    method: 'PATCH', headers: headers(), body: JSON.stringify(updates),
  })
  return res.json()
}

export async function unlinkContact(profileId, contactId) {
  await fetch(`/api/profiles/${profileId}/contacts/${contactId}/link`, { method: 'DELETE' })
}

export async function startMethodVerification(profileId, contactId, methodId) {
  const res = await fetch(
    `/api/profiles/${profileId}/contacts/${contactId}/methods/${methodId}/verify/start`,
    { method: 'POST', headers: headers() },
  )
  if (!res.ok) {
    let detail = `Could not start verification (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    const err = new Error(detail); err.status = res.status; throw err
  }
  return res.json()
}

export async function confirmMethodVerification(profileId, contactId, methodId, code) {
  const res = await fetch(
    `/api/profiles/${profileId}/contacts/${contactId}/methods/${methodId}/verify/confirm`,
    { method: 'POST', headers: headers(), body: JSON.stringify({ code }) },
  )
  if (!res.ok) {
    let detail = `Verification failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function fetchContactGroups(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/contact-groups/`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function createContactGroup(profileId, name) {
  const res = await fetch(`/api/profiles/${profileId}/contact-groups/`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ name }),
  })
  return res.json()
}

export async function createMediaShare(profileId, mediaId, expiresInHours = 72) {
  const res = await fetch(`/api/profiles/${profileId}/media-shares/`, {
    method: 'POST', headers: headers(),
    body: JSON.stringify({ media_id: mediaId, expires_in_hours: expiresInHours }),
  })
  if (!res.ok) throw new Error(`Could not create share link (HTTP ${res.status})`)
  return res.json()
}

// Role labels shown in the contact editor (keys must match backend CONTACT_ROLES).
export const CONTACT_ROLE_OPTIONS = [
  ['pediatrician', 'Pediatrician'],
  ['speech_therapist', 'Speech Therapist'],
  ['occupational_therapist', 'Occupational Therapist'],
  ['other_clinician', 'Other Clinician'],
  ['educator', 'Educator / Teacher'],
  ['childcare', 'Childcare / Daycare'],
  ['caregiver', 'Caregiver'],
  ['family', 'Family'],
  ['guardian', 'Guardian / Co-parent'],
  ['emergency_contact', 'Emergency Contact'],
  ['other', 'Other'],
]

// --- Email Center (v6 Pass 5) -------------------------------------------------

export async function fetchEmailFacts(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/email/facts`, { headers: headers() })
  if (!res.ok) return null
  return res.json()
}

export async function fetchEmailRecipients(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/email/recipients`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function createEmailDraft(profileId, payload) {
  const res = await fetch(`/api/profiles/${profileId}/email/drafts`, {
    method: 'POST', headers: headers(), body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let detail = `Could not create draft (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function aiEmailDraft(profileId, payload) {
  const res = await fetch(`/api/profiles/${profileId}/email/drafts/ai-draft`, {
    method: 'POST', headers: headers(), body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let detail = `AI draft failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function fetchEmailDrafts(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/email/drafts`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}

export async function previewEmailDraft(profileId, draftId) {
  const res = await fetch(`/api/profiles/${profileId}/email/drafts/${draftId}/preview`, {
    method: 'POST', headers: headers(),
  })
  if (!res.ok) {
    let detail = `Preview failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function sendEmailDraft(profileId, draftId) {
  const res = await fetch(`/api/profiles/${profileId}/email/drafts/${draftId}/send`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ confirm: true }),
  })
  if (!res.ok) {
    let detail = `Send failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b?.detail) detail = typeof b.detail === 'string' ? b.detail : detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function fetchEmailMessages(profileId) {
  const res = await fetch(`/api/profiles/${profileId}/email/messages`, { headers: headers() })
  if (!res.ok) return []
  return res.json()
}
