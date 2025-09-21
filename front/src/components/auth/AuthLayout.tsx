/**
 * AuthLayout Component for Sayar WhatsApp Commerce Platform
 * Professional two-column authentication layout inspired by modern SaaS applications
 */

import React from 'react'
import { Link } from 'react-router-dom'

interface AuthLayoutProps {
  title: string
  description: string
  children: React.ReactNode
  footerText?: string
  footerLink?: { text: string; href: string }
}

const AuthLayout: React.FC<AuthLayoutProps> = ({
  title,
  description,
  children,
  footerText,
  footerLink,
}) => {
  return (
    <div className="min-h-screen flex">
      {/* Left Column - Brand/Logo Section */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary justify-center items-center relative">
        <div className="absolute inset-0 bg-black opacity-100" />
        <div className="relative z-10 px-1 max-w-xl">
          <div className="mb-6">
            <img src="/logo.png" alt="Sayar" className="h-12 md:h-14 w-auto" />
          </div>
          <p className="text-xl text-white opacity-90 mb-8">
            The complete WhatsApp commerce solution for your business
          </p>
          <div className="grid grid-cols-2 gap-4 text-white">
            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Easy Integration</h3>
              <p className="text-sm opacity-80">Streamline your WhatsApp commerce process and increase efficiency.</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Multi-tenant</h3>
              <p className="text-sm opacity-80">Manage multiple businesses with a single account.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Form Section */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 lg:p-12 bg-gray-50">
        <div className="w-full max-w-md space-y-8">
          {/* Header */}
          <div className="text-center lg:text-left">
            {/* Mobile logo */}
            <div className="lg:hidden flex justify-center mb-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-xl font-bold text-white">S</span>
                </div>
                <span className="text-2xl font-bold text-gray-900">Sayar</span>
              </div>
            </div>

            
          </div>

          {/* Form Content */}
          
          
          <div className="bg-white px-8 py-8 rounded-xl shadow-sm border border-gray-200">
            <div className="space-y-3">
              <h3 className="text-3xl font-bold tracking-tight text-center">{title}</h3>
              <p className="text-muted-foreground text-center">{description}</p>
            </div>
          <br/>
            {children}
          </div>

          {/* Footer */}
          {footerText && footerLink && (
            <p className="text-center text-sm text-gray-600">
              {footerText}{' '}
              <Link
                to={footerLink.href}
                className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
              >
                {footerLink.text}
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default AuthLayout