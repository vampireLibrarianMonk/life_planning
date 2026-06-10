import { getToken } from './auth'

const headers = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${getToken()}`,
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
    headers: { 'Authorization': `Bearer ${getToken()}` },
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
    headers: { 'Authorization': `Bearer ${getToken()}` },
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
