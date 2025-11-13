# Landing Page Example

## Overview

This is a simple, production-ready landing page for your VLA API. It's a single HTML file with no dependencies - just copy it to your server and you're done.

## Features

- **Responsive Design** - Works on desktop, tablet, and mobile
- **Modern UI** - Clean gradient design with smooth animations
- **Sections Included:**
  - Hero with CTA buttons
  - Features grid
  - Pricing cards (Free, Pro, Enterprise)
  - Code example
  - Contact form
- **No Dependencies** - Pure HTML/CSS, no JavaScript frameworks
- **Fast Loading** - Single file, <10KB

## How to Use

### Option 1: Static Hosting (Easiest)

Deploy to any static host:

```bash
# Netlify
netlify deploy --dir=examples/landing-page

# Vercel
vercel examples/landing-page

# GitHub Pages
# Just push to gh-pages branch
```

**Cost:** $0/month

### Option 2: S3 + CloudFront (Scalable)

```bash
# Upload to S3
aws s3 sync examples/landing-page s3://yourbucket/ --acl public-read

# Enable website hosting
aws s3 website s3://yourbucket/ --index-document index.html

# Optional: Add CloudFront CDN
```

**Cost:** $0.50-$5/month

### Option 3: Same Server as API (Simple)

```bash
# Copy to server
scp examples/landing-page/index.html ubuntu@YOUR_SERVER:/var/www/html/

# Configure NGINX to serve it
```

Add to your NGINX config:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    root /var/www/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}
```

**Cost:** $0 (uses existing server)

## Customization

### 1. Update Domain/Email

Find and replace in `index.html`:
- `yourdomain.com` → Your actual domain
- `hello@yourdomain.com` → Your email
- `YOUR_FORM_ID` → Your Formspree form ID (see below)

### 2. Setup Contact Form

The form uses [Formspree](https://formspree.io/) (free for 50 submissions/month):

1. Go to https://formspree.io/
2. Sign up (free)
3. Create new form
4. Copy form ID
5. Replace `YOUR_FORM_ID` in the HTML

**Alternative:** Use Google Forms, Netlify Forms, or your own backend

### 3. Change Colors

Edit the CSS variables at the top of `<style>`:

```css
/* Current: Purple gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Blue gradient */
background: linear-gradient(135deg, #2b5ce6 0%, #0abfff 100%);

/* Green gradient */
background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);

/* Red gradient */
background: linear-gradient(135deg, #f857a6 0%, #ff5858 100%);
```

### 4. Update Pricing

Edit the pricing section to match your actual tiers:

```html
<div class="pricing-card">
    <h3>Starter</h3>
    <div class="price">$29<span>/month</span></div>
    <ul class="pricing-features">
        <li>50,000 API calls/month</li>
        <li>60 requests/minute</li>
        <!-- Add your features -->
    </ul>
</div>
```

### 5. Add Documentation Link

Once you create docs, update the button:

```html
<a href="https://docs.yourdomain.com" class="btn btn-secondary">View Documentation</a>
```

### 6. Add Analytics

Add before `</head>`:

**Google Analytics:**
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

**Plausible (privacy-friendly):**
```html
<script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

### 7. SEO Optimization

Update meta tags:

```html
<meta name="description" content="Your actual description">
<meta name="keywords" content="vla, robotics, api, machine learning">
<meta property="og:title" content="VLA Inference API">
<meta property="og:description" content="Your description">
<meta property="og:image" content="https://yourdomain.com/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
```

## Advanced: Multi-Page Version

If you want separate pages:

```
landing-page/
  index.html        # Homepage
  docs.html         # Documentation
  pricing.html      # Detailed pricing
  about.html        # About page
  privacy.html      # Privacy policy
  terms.html        # Terms of service
  styles.css        # Shared styles
```

## Next Steps

1. **Deploy this landing page** to yourdomain.com
2. **Setup contact form** (Formspree or email)
3. **Create documentation** (see docs/ folder options)
4. **Build user dashboard** (see PRODUCTION_DEPLOYMENT_GUIDE.md)
5. **Add payment integration** (Stripe)

## Pro Tips

### Improve Conversions

1. **Add Social Proof**
   - Customer logos
   - Testimonials
   - "Used by X companies"

2. **Add Demo Video**
   - Show API in action
   - Embed YouTube/Loom video

3. **Live API Playground**
   - Let users test API without signing up
   - Use RunKit or CodeSandbox embed

4. **Case Studies**
   - Show real-world applications
   - Before/after metrics

### Performance

1. **Optimize Images**
   - Use WebP format
   - Compress with TinyPNG

2. **Add CDN**
   - Cloudflare (free)
   - AWS CloudFront

3. **Minify Code**
   ```bash
   # Minify HTML
   html-minifier index.html > index.min.html
   ```

### Accessibility

1. **Add ARIA labels**
2. **Test with screen readers**
3. **Ensure keyboard navigation**
4. **High contrast mode**

## Templates & Tools

### Free Landing Page Builders
- [Carrd](https://carrd.co/) - $9-19/year
- [Webflow](https://webflow.com/) - Free tier
- [Framer](https://framer.com/) - Free tier

### Premium Templates
- [Tailwind UI](https://tailwindui.com/) - $149-$299
- [ThemeForest](https://themeforest.net/) - $10-$50
- [Creative Tim](https://www.creative-tim.com/) - Free + Premium

### Design Tools
- [Figma](https://figma.com/) - Free for design
- [Canva](https://canva.com/) - Graphics
- [Coolors](https://coolors.co/) - Color palettes

## Support

Need help customizing? Check:
- HTML/CSS basics: [MDN Web Docs](https://developer.mozilla.org/)
- Responsive design: [CSS-Tricks](https://css-tricks.com/)
- Hosting: See PRODUCTION_DEPLOYMENT_GUIDE.md

## License

This example is provided as-is for your use. Customize freely.






