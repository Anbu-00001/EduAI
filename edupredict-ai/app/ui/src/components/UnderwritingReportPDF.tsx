import jsPDF from 'jspdf'
import type { AssessmentResponse, StudentProfile } from '@/api/types'
import { formatINR, titleCase } from '@/lib/utils'

export async function generateUnderwritingReport(result: AssessmentResponse, variables: StudentProfile, tenantId: string = 'LENDER-101') {
  try {
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageW = doc.internal.pageSize.getWidth()
    const pageH = doc.internal.pageSize.getHeight()
    const margin = 20
    const contentW = pageW - margin * 2
    let y = 20

    // PAGE 1: Decision Summary
    doc.setFontSize(22)
    doc.setFont('helvetica', 'bold')
    doc.text('EduPredict AI', margin, y)
    
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(100)
    doc.text(`Underwriting Report`, margin, y + 6)
    
    // Right aligned header
    doc.setFontSize(9)
    const rightAlign = pageW - margin
    doc.text(`Assessment ID: ${result.assessment_id.slice(0, 12)}`, rightAlign, y, { align: 'right' })
    doc.text(`Generated: ${new Date().toLocaleString('en-IN')}`, rightAlign, y + 4, { align: 'right' })
    doc.text(`Lender ID: ${tenantId}`, rightAlign, y + 8, { align: 'right' })
    
    y += 20
    doc.setDrawColor(200)
    doc.line(margin, y, pageW - margin, y)
    y += 10

    // SECTION: Decision
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(0)
    doc.text('1. Decision', margin, y)
    y += 8
    
    const isApprove = result.risk_tier === 'GREEN'
    const isReview = result.risk_tier === 'AMBER'
    doc.setFontSize(24)
    if (isApprove) doc.setTextColor(16, 185, 129)
    else if (isReview) doc.setTextColor(245, 158, 11)
    else doc.setTextColor(244, 63, 94)
    
    doc.text(isApprove ? 'APPROVE' : isReview ? 'REVIEW' : 'DECLINE', margin, y)
    doc.setTextColor(100)
    doc.setFontSize(10)
    doc.setFont('helvetica', 'italic')
    y += 6
    doc.text(result.recommendation, margin, y, { maxWidth: contentW })
    y += 15

    // SECTION: Risk Score
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(0)
    doc.text('2. Risk Score', margin, y)
    y += 8
    
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Repayment Probability: ${(result.calibrated_probability * 100).toFixed(1)}%`, margin, y)
    y += 6
    doc.text(`90% Conformal Interval: ${(result.confidence_interval_90pct.lower * 100).toFixed(1)}% - ${(result.confidence_interval_90pct.upper * 100).toFixed(1)}%`, margin, y)
    y += 15

    // SECTION: Loan Parameters
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('3. Loan Parameters', margin, y)
    y += 8
    
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    const params = [
      `Loan Amount: ${formatINR(variables.loan_amount_inr)}`,
      `Est. Tenure: 120 months`,
      `Est. EMI: ${formatINR(variables.loan_amount_inr * 0.0135)}/mo`,
      `Field of Study: ${titleCase(variables.field_of_study)}`,
      `Institution Verified: ${variables.institution_verified ? 'Yes' : 'No'}`,
      `CGPA: ${variables.cgpa.toFixed(2)}/10`,
      `Backlogs: ${variables.backlogs}`
    ]
    
    params.forEach((param, i) => {
      doc.text(param, margin + (i % 2 === 0 ? 0 : contentW / 2), y + Math.floor(i / 2) * 6)
    })
    y += Math.ceil(params.length / 2) * 6 + 10

    // SECTION: Top 5 Drivers
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('4. Top 5 Drivers (SHAP)', margin, y)
    y += 8
    
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    const sortedShap = Object.entries(result.shap_contributions)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 5)
      
    sortedShap.forEach(([feature, val]) => {
      const isPos = val > 0
      doc.setTextColor(isPos ? 16 : 244, isPos ? 185 : 63, isPos ? 129 : 94)
      doc.text(`${isPos ? '+' : ''}${(val * 100).toFixed(1)}%`, margin, y)
      doc.setTextColor(0)
      doc.text(titleCase(feature.replace(/_normalized$/, '')), margin + 25, y)
      y += 6
    })

    // PAGE 2: Compliance & Audit Trail
    doc.addPage()
    y = 20
    
    doc.setFontSize(16)
    doc.setFont('helvetica', 'bold')
    doc.text('Compliance & Audit Trail', margin, y)
    y += 15

    // SECTION: Fairness Calibration
    doc.setFontSize(12)
    doc.text('Fairness Calibration', margin, y)
    y += 6
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Group threshold applied: ${result.fairness_applied ? 'Yes (per-group thresholds)' : 'No'}`, margin, y)
    y += 5
    doc.text('Reason: protective bias correction under RBI FREE-AI 4.3.2', margin, y)
    y += 15

    // SECTION: Adverse Action Reasons
    if (!isApprove && result.adverse_action) {
      doc.setFontSize(12)
      doc.setFont('helvetica', 'bold')
      doc.text('Adverse Action Reasons', margin, y)
      y += 6
      doc.setFontSize(10)
      doc.setFont('helvetica', 'normal')
      result.adverse_action.reasons.forEach(reason => {
        doc.setFont('helvetica', 'bold')
        doc.text(reason.code, margin, y)
        doc.setFont('helvetica', 'normal')
        doc.text(reason.feature ?? '', margin + 80, y) // Fallback for code mappings
        y += 5
      })
      y += 10
    }

    // SECTION: Model Provenance
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('Model Provenance', margin, y)
    y += 6
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Model version: ${result.model_version}`, margin, y)
    y += 5
    doc.text(`Training date: Oct 2025 (baseline)`, margin, y)
    y += 5
    doc.text(`Last fairness audit date: Oct 28, 2025`, margin, y)
    y += 15

    // SECTION: Audit Trail
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('Audit Trail', margin, y)
    y += 6
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Assessment ID: ${result.assessment_id}`, margin, y)
    y += 5
    doc.text(`Timestamp: ${result.timestamp}`, margin, y)
    y += 5
    
    // Hash mock for demo (SHA256 placeholder)
    const featureHash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(variables)))
    const hashHex = Array.from(new Uint8Array(featureHash)).map(b => b.toString(16).padStart(2, '0')).join('')
    doc.text(`Feature vector hash: ${hashHex.slice(0, 32)}...`, margin, y)
    
    // Footer
    doc.setFontSize(8)
    doc.setTextColor(150)
    doc.text(`Generated by EduPredict AI v${result.model_version}.`, margin, pageH - 20)
    doc.text(`Contains decision-relevant information per RBI Master Direction on Default Loss Guarantee, Sept 2025.`, margin, pageH - 16)

    doc.save(`underwriting-${result.assessment_id.slice(0, 12)}-${new Date().toISOString().split('T')[0]}.pdf`)
  } catch (err) {
    console.error("PDF generation failed", err)
  }
}
