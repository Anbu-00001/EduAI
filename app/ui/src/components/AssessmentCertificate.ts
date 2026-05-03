import { jsPDF } from 'jspdf'

interface CertData {
  assessmentId: string
  repaymentProbability: number
  riskTier: 'GREEN' | 'AMBER' | 'RED'
  confidenceLower: number
  confidenceUpper: number
  cgpa: number
  fieldOfStudy: string
  loanAmountInr: number
  timestamp: string
  modelVersion: string
}

const FIELD_LABELS: Record<string, string> = {
  computer_science:       'Computer Science / IT',
  data_science:           'Data Science / AI',
  mba_finance:            'MBA Finance',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  civil_engineering:      'Civil Engineering',
  biotechnology:          'Biotechnology',
}

const TIER_RGB: Record<string, [number, number, number]> = {
  GREEN: [34,  197, 94],
  AMBER: [245, 158, 11],
  RED:   [239, 68,  68],
}

export function downloadAssessmentCertificate(data: CertData): void {
  // A5 landscape: 210 × 148 mm
  const doc = new jsPDF({ orientation: 'landscape', format: 'a5', unit: 'mm' })
  const W = 210
  const H = 148

  const [tr, tg, tb] = TIER_RGB[data.riskTier] ?? [148, 163, 184]

  // ── Background ────────────────────────────────────────────────────────
  doc.setFillColor(10, 15, 30)
  doc.rect(0, 0, W, H, 'F')

  // ── Header band ───────────────────────────────────────────────────────
  doc.setFillColor(15, 23, 42)
  doc.rect(0, 0, W, 20, 'F')

  doc.setTextColor(148, 163, 184)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(9)
  doc.text('EDUPREDICT AI', 10, 12)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6.5)
  doc.text('Student Loan Intelligence Platform', 10, 17)

  doc.setFontSize(7)
  doc.text('INDICATIVE ASSESSMENT CERTIFICATE', W / 2, 12, { align: 'center' })

  const dateStr = new Date(data.timestamp).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6.5)
  doc.text(dateStr, W - 10, 12, { align: 'right' })
  doc.text(`v${data.modelVersion}`, W - 10, 17, { align: 'right' })

  // ── Header divider ────────────────────────────────────────────────────
  doc.setDrawColor(30, 41, 59)
  doc.setLineWidth(0.3)
  doc.line(0, 20, W, 20)

  // ── Left panel — tier badge ───────────────────────────────────────────
  const cx = 42
  const cy = 80

  // Outer halo (dark tinted ring)
  doc.setFillColor(
    Math.round(tr * 0.12 + 10),
    Math.round(tg * 0.12 + 15),
    Math.round(tb * 0.12 + 30),
  )
  doc.circle(cx, cy, 31, 'F')

  // Inner filled circle (tier colour, semi-dark)
  doc.setFillColor(
    Math.round(tr * 0.25 + 8),
    Math.round(tg * 0.25 + 12),
    Math.round(tb * 0.25 + 25),
  )
  doc.circle(cx, cy, 28, 'F')

  // Tier-coloured ring outline
  doc.setDrawColor(tr, tg, tb)
  doc.setLineWidth(1.8)
  doc.circle(cx, cy, 28, 'D')

  // Probability text
  doc.setTextColor(tr, tg, tb)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(28)
  doc.text(`${Math.round(data.repaymentProbability * 100)}%`, cx, cy + 4, { align: 'center' })

  doc.setFontSize(6.5)
  doc.setTextColor(148, 163, 184)
  doc.text('repayment likelihood', cx, cy + 13, { align: 'center' })

  // Tier badge pill
  doc.setFillColor(tr, tg, tb)
  doc.roundedRect(cx - 14, cy + 19, 28, 8, 2, 2, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  const tierLabel =
    data.riskTier === 'GREEN' ? 'LOW RISK' :
    data.riskTier === 'AMBER' ? 'MODERATE' : 'HIGH RISK'
  doc.text(tierLabel, cx, cy + 24.5, { align: 'center' })

  // Confidence interval
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6)
  doc.setTextColor(100, 116, 139)
  doc.text('90% Confidence Interval', cx, cy + 36, { align: 'center' })
  doc.setTextColor(148, 163, 184)
  doc.setFontSize(7)
  doc.text(
    `${(data.confidenceLower * 100).toFixed(1)}%  –  ${(data.confidenceUpper * 100).toFixed(1)}%`,
    cx, cy + 42, { align: 'center' },
  )

  // ── Centre divider ────────────────────────────────────────────────────
  doc.setDrawColor(30, 41, 59)
  doc.setLineWidth(0.3)
  doc.line(83, 25, 83, H - 14)

  // ── Right panel — profile details ─────────────────────────────────────
  const rx = 92
  let y = 33

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(9)
  doc.setTextColor(226, 232, 240)
  doc.text('Profile Summary', rx, y)
  y += 10

  const rows: [string, string][] = [
    ['Field of Study', FIELD_LABELS[data.fieldOfStudy] ?? data.fieldOfStudy],
    ['CGPA',          `${data.cgpa.toFixed(1)} / 10.0`],
    ['Loan Amount',   `INR ${(data.loanAmountInr / 100_000).toFixed(1)} Lakh`],
    ['Est. EMI',      `INR ${Math.round(data.loanAmountInr * 0.01349).toLocaleString('en-IN')} /month`],
  ]

  rows.forEach(([label, val]) => {
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7)
    doc.setTextColor(100, 116, 139)
    doc.text(label, rx, y)

    doc.setFont('helvetica', 'bold')
    doc.setTextColor(203, 213, 225)
    doc.text(val, rx + 48, y)
    y += 8.5
  })

  // Compliance box
  y += 4
  doc.setFillColor(15, 23, 42)
  doc.roundedRect(rx, y, W - rx - 10, 24, 2, 2, 'F')

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(6.5)
  doc.setTextColor(34, 197, 94)
  doc.text('Fairness: DPDP Act 2023 Compliant', rx + 3, y + 7)

  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.setFontSize(6)
  doc.text('Demographic parity audited · Conformal prediction (alpha = 0.10)', rx + 3, y + 13)
  doc.text('RBI FREE-AI Framework, August 2025 · Not a credit decision', rx + 3, y + 18.5)

  // ── Footer ─────────────────────────────────────────────────────────────
  doc.setDrawColor(30, 41, 59)
  doc.setLineWidth(0.3)
  doc.line(0, H - 12, W, H - 12)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(5.5)
  doc.setTextColor(71, 85, 105)
  doc.text(`Assessment ID: ${data.assessmentId}`, 10, H - 6)
  doc.text(
    'FOR INFORMATIONAL PURPOSES ONLY — NOT A BINDING CREDIT DECISION',
    W / 2, H - 6, { align: 'center' },
  )
  doc.text('edupredict.ai', W - 10, H - 6, { align: 'right' })

  doc.save(`EduPredict_Certificate_${data.assessmentId.slice(0, 8)}.pdf`)
}
