import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Accessibility Statement - Plinto',
  description: 'Plinto is committed to ensuring digital accessibility for all users.',
}

export default function AccessibilityPage() {
  return (
    <div className="bg-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="prose prose-lg max-w-none">
          <h1>Accessibility Statement</h1>
          
          <p className="lead">
            Plinto is committed to ensuring digital accessibility for people with disabilities. 
            We are continually improving the user experience for everyone and applying the 
            relevant accessibility standards.
          </p>

          <h2>Conformance Status</h2>
          <p>
            The <a href="https://www.w3.org/WAI/standards-guidelines/wcag/">Web Content Accessibility Guidelines (WCAG)</a> defines 
            requirements for designers and developers to improve accessibility for people with disabilities. 
            It defines three levels of conformance: Level A, Level AA, and Level AAA.
          </p>
          <p>
            <strong>Plinto is fully conformant with WCAG 2.1 Level AA.</strong> Fully conformant means that 
            the content fully conforms to the accessibility standard without any exceptions.
          </p>

          <h2>Accessibility Features</h2>
          
          <h3>Keyboard Navigation</h3>
          <ul>
            <li>All interactive elements are keyboard accessible</li>
            <li>Logical tab order throughout the site</li>
            <li>Visible focus indicators on all interactive elements</li>
            <li>Skip links to bypass repetitive navigation</li>
          </ul>

          <h3>Screen Reader Support</h3>
          <ul>
            <li>Semantic HTML structure</li>
            <li>ARIA labels and roles where appropriate</li>
            <li>Alternative text for all images</li>
            <li>Descriptive link text</li>
            <li>Form labels and error messages</li>
          </ul>

          <h3>Visual Design</h3>
          <ul>
            <li>Color contrast ratio of at least 4.5:1 for normal text</li>
            <li>Color contrast ratio of at least 3:1 for large text</li>
            <li>Information is not conveyed by color alone</li>
            <li>Resizable text up to 200% without loss of functionality</li>
            <li>Responsive design for various screen sizes</li>
          </ul>

          <h3>Content</h3>
          <ul>
            <li>Clear and consistent navigation</li>
            <li>Descriptive headings and labels</li>
            <li>Plain language where possible</li>
            <li>Error identification and suggestions</li>
          </ul>

          <h2>Technical Specifications</h2>
          <p>
            Accessibility relies on the following technologies to work with the particular 
            combination of web browser and assistive technologies or plugins installed:
          </p>
          <ul>
            <li>HTML5</li>
            <li>CSS3</li>
            <li>JavaScript</li>
            <li>WAI-ARIA</li>
          </ul>

          <h2>Limitations and Alternatives</h2>
          <p>
            Despite our best efforts to ensure accessibility, there may be some limitations. 
            Below is a description of known limitations and potential solutions:
          </p>
          <ul>
            <li>
              <strong>Third-party content</strong>: Some third-party content may not be fully accessible. 
              We work with vendors to ensure their content meets accessibility standards.
            </li>
            <li>
              <strong>PDF documents</strong>: We strive to make all PDF documents accessible and provide 
              alternative formats when possible.
            </li>
          </ul>

          <h2>Assessment Approach</h2>
          <p>
            Plinto assessed the accessibility of this website by the following approaches:
          </p>
          <ul>
            <li>Self-evaluation using automated testing tools</li>
            <li>Manual testing with keyboard navigation</li>
            <li>Screen reader testing (NVDA, JAWS, VoiceOver)</li>
            <li>Color contrast analysis</li>
            <li>Third-party accessibility audits</li>
          </ul>

          <h2>Feedback</h2>
          <p>
            We welcome your feedback on the accessibility of Plinto. Please let us know if you 
            encounter accessibility barriers:
          </p>
          <ul>
            <li>
              Email: <a href="mailto:accessibility@plinto.dev">accessibility@plinto.dev</a>
            </li>
            <li>
              GitHub Issues: <a href="https://github.com/madfam-io/plinto/issues">Report an accessibility issue</a>
            </li>
          </ul>
          <p>
            We try to respond to feedback within 2 business days.
          </p>

          <h2>Compatibility with Browsers and Assistive Technology</h2>
          <p>
            Plinto is designed to be compatible with the following assistive technologies:
          </p>
          <ul>
            <li>Latest versions of Chrome, Firefox, Safari, and Edge</li>
            <li>Screen readers: NVDA, JAWS, VoiceOver</li>
            <li>Voice recognition software</li>
            <li>Screen magnification software</li>
          </ul>

          <h2>Formal Complaints</h2>
          <p>
            If you are not satisfied with our response to your accessibility feedback, you may 
            file a formal complaint by emailing <a href="mailto:legal@plinto.dev">legal@plinto.dev</a>.
          </p>

          <h2>Last Updated</h2>
          <p>
            This statement was last updated on <strong>November 14, 2025</strong>.
          </p>
        </div>
      </div>
    </div>
  )
}
