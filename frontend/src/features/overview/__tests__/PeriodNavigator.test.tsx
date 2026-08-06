import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import PeriodNavigator from '../PeriodNavigator';

const periods = ['2017-01', '2017-02', '2017-03'];

describe('PeriodNavigator', () => {
  it('supports direct, previous, and next month selection', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PeriodNavigator
        periods={periods}
        selectedPeriod="2017-02"
        onChange={onChange}
        isPlaying={false}
        onPlayingChange={vi.fn()}
      />,
    );

    expect(screen.getByRole('heading', { name: 'February 2017' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show previous month' }));
    await user.click(screen.getByRole('button', { name: 'Show next month' }));
    await user.click(screen.getByRole('tab', { name: 'March 2017' }));

    expect(onChange).toHaveBeenNthCalledWith(1, '2017-01');
    expect(onChange).toHaveBeenNthCalledWith(2, '2017-03');
    expect(onChange).toHaveBeenNthCalledWith(3, '2017-03');
  });

  it('does not render a selector when no monthly periods exist', () => {
    const { container } = render(
      <PeriodNavigator
        periods={[]}
        selectedPeriod=""
        onChange={vi.fn()}
        isPlaying={false}
        onPlayingChange={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
