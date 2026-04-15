/**
 * The manual upload workflow has been removed.
 * PaperLens now uses folder-based ingestion only.
 * This page redirects to /ingest for backward compatibility.
 */
import { redirect } from 'next/navigation';

export default function UploadPage() {
  redirect('/ingest');
}
