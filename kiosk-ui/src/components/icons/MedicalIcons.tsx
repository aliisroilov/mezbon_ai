import { cn } from "../../lib/cn";

interface IconProps {
  className?: string;
}

export function HeartPulseIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19.5 12.572l-7.5 7.428-7.5-7.428A5 5 0 1 1 12 6.006a5 5 0 1 1 7.5 6.572" />
      <path d="M7 12h2l2-3 2 6 2-3h2" />
    </svg>
  );
}

export function ToothIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2C8 2 5 5 5 8c0 2 .5 3.5 1 5 .8 2.4 1 4 1.5 6 .3 1 .8 1.5 1.5 1.5s1.2-.5 1.5-2c.3-1.5.5-2 1.5-2s1.2.5 1.5 2c.3 1.5.8 2 1.5 2s1.2-.5 1.5-1.5c.5-2 .7-3.6 1.5-6 .5-1.5 1-3 1-5 0-3-3-6-7-6z" />
    </svg>
  );
}

export function BabyIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="5" />
      <path d="M12 13c-4 0-7 2-7 5v1h14v-1c0-3-3-5-7-5z" />
      <circle cx="10" cy="7.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="14" cy="7.5" r="0.5" fill="currentColor" stroke="none" />
      <path d="M10.5 9.5c.5.5 2.5.5 3 0" />
    </svg>
  );
}

export function BrainIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a5 5 0 0 0-4.5 2.8A4 4 0 0 0 4 9a4 4 0 0 0 1.2 2.8A4.5 4.5 0 0 0 7 17.5V20h4v-8" />
      <path d="M12 2a5 5 0 0 1 4.5 2.8A4 4 0 0 1 20 9a4 4 0 0 1-1.2 2.8A4.5 4.5 0 0 1 17 17.5V20h-4v-8" />
      <path d="M8 10h.01M16 10h.01" />
    </svg>
  );
}

export function StethoscopeIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3" />
      <path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4" />
      <circle cx="20" cy="10" r="2" />
    </svg>
  );
}

export function EyeIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function SkinIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
      <path d="M8 12h.01M12 12h.01M16 12h.01" />
      <path d="M7 8l2 2M15 8l2 2" />
    </svg>
  );
}

export function BoneIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.2 3.4a2 2 0 0 1 3.4 2l-.5 1a2 2 0 0 0 .5 2.1l.5.5a2 2 0 0 1-1 3.4L18 13l-7 7-2-.5a2 2 0 0 1-1.4-1L7 17.2a2 2 0 0 1 .3-2.1l.5-.5a2 2 0 0 0-.4-2.9L6.8 11a2 2 0 0 1 0-3.4l1.2-.5A2 2 0 0 0 9.4 5l.5-1.2a2 2 0 0 1 3.4 0l.5.5a2 2 0 0 0 2 .7L17.2 3.4z" />
    </svg>
  );
}

export function HospitalIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18" />
      <path d="M5 21V7l8-4 8 4v14" />
      <rect x="9" y="9" width="6" height="6" rx="0.5" />
      <line x1="12" y1="9" x2="12" y2="15" />
      <line x1="9" y1="12" x2="15" y2="12" />
    </svg>
  );
}

export function EarIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8.5a6.5 6.5 0 1 1 13 0c0 6-6 6.5-6 10.5" />
      <path d="M15 8.5a2.5 2.5 0 0 0-5 0v1a2 2 0 0 0 4 0" />
      <circle cx="13" cy="19" r="1" />
    </svg>
  );
}

export function ButterflyIcon({ className }: IconProps) {
  return (
    <svg className={cn("h-6 w-6", className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v18" />
      <path d="M3.5 8C5 5 8 3 12 3c4 0 7 2 8.5 5C22 11 22 14 20 16c-2 2-5 2-8 2s-6 0-8-2c-2-2-2-5-.5-8z" />
    </svg>
  );
}

// Icon map by department name keyword
export const MEDICAL_ICON_MAP: Record<string, React.FC<IconProps>> = {
  cardiology: HeartPulseIcon,
  kardiologiya: HeartPulseIcon,
  stomatology: ToothIcon,
  stomatologiya: ToothIcon,
  pediatrics: BabyIcon,
  pediatriya: BabyIcon,
  neurology: BrainIcon,
  nevrologiya: BrainIcon,
  therapy: StethoscopeIcon,
  terapiya: StethoscopeIcon,
  ophthalmology: EyeIcon,
  okulistika: EyeIcon,
  dermatology: SkinIcon,
  dermatologiya: SkinIcon,
  orthopedics: BoneIcon,
  ortopediya: BoneIcon,
  gynecology: BabyIcon,
  ginekologiya: BabyIcon,
  urology: HospitalIcon,
  urologiya: HospitalIcon,
  ent: EarIcon,
  lor: EarIcon,
  surgery: HospitalIcon,
  xirurgiya: HospitalIcon,
  endocrinology: ButterflyIcon,
  endokrinologiya: ButterflyIcon,
  mammologiya: HeartPulseIcon,
  mammology: HeartPulseIcon,
  reanimatsiya: HospitalIcon,
  reanimation: HospitalIcon,
  radiologiya: EyeIcon,
  radiology: EyeIcon,
};

export function getMedicalIcon(name: string): React.FC<IconProps> {
  const lower = name.toLowerCase();
  for (const [key, Icon] of Object.entries(MEDICAL_ICON_MAP)) {
    if (lower.includes(key)) return Icon;
  }
  return HospitalIcon;
}
