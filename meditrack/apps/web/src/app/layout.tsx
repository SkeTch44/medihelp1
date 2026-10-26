import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'MediTrack — your health routine, made easier', description: 'Gentle reminders and simple check-ins for medication, supplements, hydration, movement and daily wellness.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
