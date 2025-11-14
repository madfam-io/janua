import Link from 'next/link'
import { HeroSection } from '@/components/HeroSection'
import { FeaturesGrid } from '@/components/FeaturesGrid'
import { CTASection } from '@/components/CTASection'

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <FeaturesGrid />
      <CTASection />
    </>
  )
}
