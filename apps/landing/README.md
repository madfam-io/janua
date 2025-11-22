# Janua Landing Site

Next.js landing and documentation site for Janua authentication platform.

## Features

- **Homepage**: Hero section, features grid, and CTA
- **Features Page**: Detailed feature descriptions with code examples
- **Pricing Page**: Tier comparison and feature matrix
- **Documentation**: Comprehensive guides and API reference
- **Comparison**: Side-by-side comparison with competitors

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **TypeScript**: Full type safety
- **Icons**: SVG icons
- **Deployment**: Vercel, Netlify, or self-hosted

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
apps/landing/
├── app/
│   ├── layout.tsx         # Root layout with navigation
│   ├── page.tsx           # Homepage
│   ├── features/          # Features page
│   ├── pricing/           # Pricing page
│   ├── compare/           # Comparison page
│   └── docs/              # Documentation hub
│       ├── layout.tsx     # Docs sidebar navigation
│       ├── page.tsx       # Docs index
│       ├── quickstart/    # Quickstart guide
│       └── ...            # Other doc pages
├── components/
│   ├── Navigation.tsx     # Main navigation bar
│   ├── Footer.tsx         # Site footer
│   ├── HeroSection.tsx    # Homepage hero
│   ├── FeaturesGrid.tsx   # Features showcase
│   ├── CodeExample.tsx    # Code snippet component
│   └── CTASection.tsx     # Call-to-action component
└── public/                # Static assets
```

## Content Validation

All content claims are validated against actual implementation:

- **Features**: Every listed feature is implemented and tested
- **Code Examples**: All code snippets are tested and working
- **Pricing**: Tiers match actual billing service limits
- **API Docs**: Endpoints match actual API implementation

## SEO Optimization

- Semantic HTML structure
- Meta tags for all pages
- Open Graph tags
- Sitemap generation
- Structured data markup

## Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader optimized
- Color contrast compliance
- Focus indicators
- Skip links

## Performance

- Lighthouse score >90
- Image optimization
- Code splitting
- Static generation where possible
- Minimal JavaScript bundle

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Self-Hosted

```bash
# Build
npm run build

# Start server
npm start
```

### Docker

```bash
# Build image
docker build -t janua-landing .

# Run container
docker run -p 3000:3000 janua-landing
```

## Environment Variables

```bash
# Optional: Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX

# Optional: API URL for live demos
NEXT_PUBLIC_API_URL=https://api.janua.dev
```

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

AGPL-3.0 License - see main repository [LICENSE](../../LICENSE) file.
