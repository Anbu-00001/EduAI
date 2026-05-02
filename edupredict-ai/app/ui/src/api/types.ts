import { z } from 'zod'

export const FIELDS = [
  "computer_science", "data_science", "mba_finance",
  "mechanical_engineering", "electrical_engineering",
  "civil_engineering", "biotechnology"
] as const

export const ConsentBlockSchema = z.object({
  data_sources: z.array(z.string()).min(1),
  notice_version: z.string().default('1.0'),
})

export const StudentProfileSchema = z.object({
  cgpa:                     z.number().min(0).max(10, 'CGPA must be 0–10'),
  internships_count:        z.number().int().min(0).max(10),
  backlogs:                 z.number().int().min(0).max(20),
  field_of_study:           z.enum(FIELDS),
  college_placement_rate:   z.number().min(0).max(100),
  loan_amount_inr:          z.number().min(10_000, 'Minimum ₹10,000').max(5_000_000, 'Maximum ₹50L'),
  annual_family_income_inr: z.number().min(0).optional(),
  user_hash:                z.string().optional(),
  has_consent:              z.literal(true, {
    errorMap: () => ({ message: 'Explicit consent required under DPDP Act 2023' })
  }),
  cgpa_verified:            z.boolean().default(false),
  institution_verified:     z.boolean().default(false),
  consent:                  ConsentBlockSchema.optional(),
})

export type StudentProfile = z.infer<typeof StudentProfileSchema>


export interface AssessmentResponse {
  assessment_id:              string
  repayment_probability:      number
  calibrated_probability:     number
  p_model:                    number
  p_cohort:                   number
  p_blended:                  number
  /** Legacy nested confidence interval — prefer confidence_lower/confidence_upper */
  confidence_interval_90pct:  { lower: number; upper: number }
  /** Flat confidence bounds (Phase 2+) — use these in preference to confidence_interval_90pct */
  confidence_lower:           number
  confidence_upper:           number
  risk_tier:                  'GREEN' | 'AMBER' | 'RED'
  recommendation:             string
  potential_score:            number
  shap_contributions:         Record<string, number>
  counterfactual:             Record<string, any> | null
  adverse_action:             AdverseAction | null
  fairness_applied:           boolean
  temporal_features_estimated: boolean
  fairness_note:              string
  model_version:              string
  timestamp:                  string
}

export interface AdverseAction {
  adverse_action_required: boolean
  reasons: Array<{ code: string; reason?: string; feature?: string; impact?: number }>
  notice:  string
  rbi_reference: string
}

export interface FreshnessSource {
  name:              string
  freshness_weight:  number
  reliability_score: number
  last_fetched_unix: number
}

export interface FreshnessResponse {
  sources:        FreshnessSource[]
  cache_age_h:    number
  status:         'fresh' | 'stale' | 'critical'
  circuit_states: Record<string, 'closed' | 'open' | 'half_open'>
}
