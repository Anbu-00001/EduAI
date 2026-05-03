import * as Tooltip from '@radix-ui/react-tooltip'
import { CheckCircle, Circle } from 'lucide-react'

interface VerifiedBadgeProps {
  verified: boolean
  source?: string
}

export default function VerifiedBadge({ verified, source }: VerifiedBadgeProps) {
  const tooltipText = verified
    ? `Verified via DigiLocker${source ? ` (${source})` : ''}. Data integrity guaranteed by National Academic Depository.`
    : 'Self-reported by applicant. Not verified against official records.'

  return (
    <Tooltip.Provider>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span className="inline-flex items-center gap-1 cursor-default">
            {verified ? (
              <>
                <CheckCircle className="w-3.5 h-3.5 text-green" />
                <span className="text-[10px] font-medium text-green-text">Verified via DigiLocker</span>
              </>
            ) : (
              <>
                <Circle className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-[10px] text-slate-500">Self-reported</span>
              </>
            )}
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="max-w-[200px] p-2.5 text-[11px] text-slate-300 bg-card border border-border-2 rounded-xl shadow-xl leading-relaxed"
            sideOffset={5}
          >
            {tooltipText}
            <Tooltip.Arrow className="fill-card" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}
