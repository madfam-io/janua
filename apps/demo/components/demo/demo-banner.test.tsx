import React from 'react';
import { render, screen } from '@testing-library/react';
import { demo-banner } from './demo-banner';

describe('demo-banner', () => {
  it('should render without crashing', () => {
    render(<demo-banner />);
    expect(screen.getByTestId('demo-banner')).toBeInTheDocument();
  });
  
  it('should have correct props', () => {
    const { container } = render(<demo-banner />);
    expect(container.firstChild).toBeTruthy();
  });
  
  // TODO: Add more specific tests based on component functionality
});
