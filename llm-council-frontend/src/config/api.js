import axios from 'axios'
import versionData from '../../../version.json'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export const API_KEY = import.meta.env.VITE_API_KEY || ''
export const FRONTEND_URL = import.meta.env.VITE_FRONTEND_URL || window.location.origin
export const FRONTEND_VERSION = versionData.version

// Create axios instance with default config
export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
})
