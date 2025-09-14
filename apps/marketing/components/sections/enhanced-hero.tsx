'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Shield, Zap, Globe, Check, Building2, CreditCard } from 'lucide-react'
import { Button } from '@plinto/ui'
import { Badge } from '@plinto/ui'

interface GeoLocation {
  country: string
  currency: string
  paymentProvider: 'conekta' | 'fungies'
}

interface LiveMetrics {
  activeUsers: number
  uptime: string
  responseTime: number
  authRequests: number
}

export function EnhancedHeroSection() {
  const [geoLocation, setGeoLocation] = useState<GeoLocation>({
    country: 'US',
    currency: 'USD',
    paymentProvider: 'fungies'
  })

  const [liveMetrics, setLiveMetrics] = useState<LiveMetrics>({
    activeUsers: 15420,
    uptime: '99.99%',
    responseTime: 28,
    authRequests: 2450000
  })

  // Detect user location
  useEffect(() => {
    fetch('/api/geo')
      .then(res => res.json())
      .then(data => {
        if (data.country === 'MX') {
          setGeoLocation({
            country: 'MX',
            currency: 'MXN',
            paymentProvider: 'conekta'
          })
        }
      })
      .catch(() => {
        // Default to international
      })
  }, [])

  // Simulate live metrics
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveMetrics(prev => ({
        ...prev,
        activeUsers: prev.activeUsers + Math.floor(Math.random() * 10),
        authRequests: prev.authRequests + Math.floor(Math.random() * 100)
      }))
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const heroContent = {
    MX: {
      headline: "Plataforma de Identidad Empresarial Hecha para México",
      subheadline: "Paga en pesos con Conekta. Cumplimiento LGPD automático. Migración sin tiempo de inactividad desde cualquier proveedor.",
      cta: "Comenzar Prueba Gratuita",
      secondaryCta: "Ver Demo Empresarial",
      trustSignals: [
        "Integración Conekta",
        "Cumplimiento LGPD",
        "Soporte en Español 24/7",
        "Facturación en Pesos"
      ]
    },
    International: {
      headline: "Enterprise Identity Platform Built for Scale",
      subheadline: "Sub-30ms authentication globally. SCIM, SSO, compliance automation, and zero-trust security. Migrate from any provider with zero downtime.",
      cta: "Start Building Free",
      secondaryCta: "Schedule Enterprise Demo",
      trustSignals: [
        "SOC2 Type II Certified",
        "HIPAA & GDPR Ready",
        "99.99% Uptime SLA",
        "Global Payment Support"
      ]
    }
  }

  const content = geoLocation.country === 'MX' ? heroContent.MX : heroContent.International

  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-purple-950" />
        <motion.div
          animate={{
            backgroundPosition: ['0% 0%', '100% 100%'],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            repeatType: 'reverse',
          }}
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%239C92AC" fill-opacity="0.1"%3E%3Cpath d="M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          {/* Live metrics bar */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex flex-wrap justify-center gap-4 mb-8"
          >
            <Badge variant="outline" className="px-3 py-1 bg-white/90 dark:bg-gray-900/90 backdrop-blur">
              <Zap className="w-3 h-3 mr-1 text-green-500" />
              <span className="text-xs font-mono">{liveMetrics.responseTime}ms response</span>
            </Badge>
            <Badge variant="outline" className="px-3 py-1 bg-white/90 dark:bg-gray-900/90 backdrop-blur">
              <Shield className="w-3 h-3 mr-1 text-blue-500" />
              <span className="text-xs font-mono">{liveMetrics.uptime} uptime</span>
            </Badge>
            <Badge variant="outline" className="px-3 py-1 bg-white/90 dark:bg-gray-900/90 backdrop-blur">
              <Globe className="w-3 h-3 mr-1 text-purple-500" />
              <span className="text-xs font-mono">{liveMetrics.activeUsers.toLocaleString()} active users</span>
            </Badge>
            {geoLocation.country === 'MX' && (
              <Badge variant="outline" className="px-3 py-1 bg-green-50 dark:bg-green-900/20 border-green-200">
                <CreditCard className="w-3 h-3 mr-1 text-green-600" />
                <span className="text-xs font-semibold text-green-700 dark:text-green-400">Conekta Integration</span>
              </Badge>
            )}
          </motion.div>

          {/* Main headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 dark:text-white mb-6"
          >
            {content.headline.split(' ').map((word, i) => (
              <span
                key={i}
                className={
                  word.includes('México') || word.includes('Enterprise') || word.includes('Identity')
                    ? 'text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400'
                    : ''
                }
              >
                {word}{' '}
              </span>
            ))}
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl sm:text-2xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-10"
          >
            {content.subheadline}
          </motion.p>

          {/* Payment provider badges */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex justify-center gap-4 mb-10"
          >
            {geoLocation.country === 'MX' ? (
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                  <img src="/images/conekta-logo.png" alt="Conekta" className="h-6" />
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Pagos en Pesos</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                  <Building2 className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Facturación SAT</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                  <img src="/images/fungies-logo.png" alt="Fungies" className="h-6" />
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Global Payments</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md">
                  <Globe className="w-5 h-5 text-purple-600" />
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">150+ Countries</span>
                </div>
              </div>
            )}
          </motion.div>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-4 justify-center mb-12"
          >
            <Button
              size="lg"
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-6 text-lg"
            >
              {content.cta}
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="px-8 py-6 text-lg"
            >
              {content.secondaryCta}
            </Button>
          </motion.div>

          {/* Trust signals */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="flex flex-wrap justify-center gap-6"
          >
            {content.trustSignals.map((signal, index) => (
              <div key={index} className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <Check className="w-5 h-5 text-green-500" />
                <span className="text-sm font-medium">{signal}</span>
              </div>
            ))}
          </motion.div>

          {/* Enterprise features preview */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6"
          >
            {[
              { icon: Shield, label: 'Zero-Trust Security', value: 'ML-Powered' },
              { icon: Zap, label: 'Performance', value: 'Sub-30ms' },
              { icon: Building2, label: 'Enterprise', value: 'SCIM 2.0' },
              { icon: Globe, label: 'Global Scale', value: '150+ Edge Locations' }
            ].map((feature, index) => {
              const Icon = feature.icon
              return (
                <div key={index} className="text-center">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 rounded-xl mb-2">
                    <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="text-xs font-medium text-gray-600 dark:text-gray-400">{feature.label}</div>
                  <div className="text-sm font-bold text-gray-900 dark:text-white">{feature.value}</div>
                </div>
              )
            })}
          </motion.div>
        </div>
      </div>
    </section>
  )
}