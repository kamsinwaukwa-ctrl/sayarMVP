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
      <div className="hidden lg:flex lg:flex-1 relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 px-14 py-16">
        <div className="flex flex-col justify-center w-full max-w-xl mx-auto text-white">
          {/* Logo */}
          <div className="mb-1">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                <span className="text-2xl font-bold text-blue-600">S</span>
              </div>
              <span className="text-2xl font-bold">Sayar</span>
            </div>
          </div>

          {/* Hero Content */}
          <div className="space-y-1">
            <h1 className="text-3xl font-bold leading-tight">
              AI-powered WhatsApp Commerce Platform
            </h1>
            <p className="text-lg text-blue-100 leading-relaxed">
              Empowering businesses to increase sales and streamline the entire customer journey - from acquisition, to checkout, to retention.
            </p>
            
            {/* Feature highlights */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <span>Native WhatsApp catalog integration</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <span>Automated checkout flows</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <span>Paystack & Korapay integration</span>
              </div>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-16 translate-x-16"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full translate-y-12 -translate-x-12"></div>
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

            <h2 className="text-3xl font-bold text-gray-900">{title}</h2>
            <p className="mt-2 text-gray-600">{description}</p>
          </div>

          {/* Form Content */}
          <div className="bg-white px-8 py-6 rounded-xl shadow-sm border border-gray-200">
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