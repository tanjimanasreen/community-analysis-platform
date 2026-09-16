import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CommunityEvolution from '../CommunityEvolution';
import { useCommunityEvolutionData } from '../../features/evolution/useCommunityEvolutionData';

vi.mock('../../features/evolution/useCommunityEvolutionData', () => ({
  useCommunityEvolutionData: vi.fn(),
}));
vi.mock('../../components/PageNavigationRail', () => ({
  PageNavigationRailSlot: ({ sections }) => <nav aria-label="Section rail">{sections.map((section) => <span key={section.id}>{section.label}</span>)}</nav>,
}));

const query = (data, error = null) => ({ data, error, isPending: false, refetch: vi.fn() });

const paths = [
  {
    path_id: 'path-1', display_order: 1, duration: 3, transition_count: 2,
    average_jaccard: 0.75, total_retained_members: 5, months: ['01', '02', '03'],
    steps: [
      { step_index: 0, month: '01', community_key: '1', community_id: '1', member_count: 4, members: ['u1', 'u2', 'u3', 'u4'], previous_month: null, previous_community_key: null, previous_community_id: null, jaccard_from_previous: null, retained_count: null, absolute_theme: 'Policy', weighted_theme: 'Policy', general_theme: 'Policy' },
      { step_index: 1, month: '02', community_key: '2', community_id: '2', member_count: 4, members: ['u1', 'u2', 'u3', 'u5'], previous_month: '01', previous_community_key: '1', previous_community_id: '1', jaccard_from_previous: 0.75, retained_count: 3, absolute_theme: 'Policy debate', weighted_theme: 'Policy debate', general_theme: 'Policy debate' },
      { step_index: 2, month: '03', community_key: '3', community_id: '3', member_count: 5, members: ['u1', 'u2', 'u3', 'u4', 'u5'], previous_month: '02', previous_community_key: '2', previous_community_id: '2', jaccard_from_previous: 0.71, retained_count: 4, absolute_theme: 'Legal policy', weighted_theme: 'Legal policy', general_theme: 'Legal policy' },
    ],
  },
  {
    path_id: 'path-2', display_order: 2, duration: 2, transition_count: 1,
    average_jaccard: 0.62, total_retained_members: 2, months: ['02', '03'],
    steps: [
      { step_index: 0, month: '02', community_key: '102', community_id: '102', member_count: 3, members: ['u7', 'u8', 'u9'], previous_month: null, previous_community_key: null, previous_community_id: null, jaccard_from_previous: null, retained_count: null, absolute_theme: 'Coordination', weighted_theme: 'Coordination', general_theme: 'Coordination' },
      { step_index: 1, month: '03', community_key: '103', community_id: '103', member_count: 3, members: ['u7', 'u8', 'u10'], previous_month: '02', previous_community_key: '102', previous_community_id: '102', jaccard_from_previous: 0.62, retained_count: 2, absolute_theme: 'Coordination', weighted_theme: 'Coordination', general_theme: 'Coordination' },
    ],
  },
];

const methodology = {
  content_type: 'retweet_quote', transition_threshold: 0.5, similarity_provider: 'tei',
  similarity_model: 'sentence-transformers/paraphrase-MiniLM-L6-v2',
  similarity_model_revision: 'c9a2bfebc254878aee8c3aca9e6844d5bbb102d1',
};

const mobilityByPath = {
  'path-1': [
    { path_id: 'path-1', display_order: 1, step_index: 0, month: '01', community_key: '1', community_id: '1', member_count: 4, size_delta: null, existing_count: 4, new_count: 0, lost_count: 0, reappearing_count: 0, members: ['u1', 'u2', 'u3', 'u4'], existing_members: ['u1', 'u2', 'u3', 'u4'], new_members: [], lost_members: [], reappearing_members: [] },
    { path_id: 'path-1', display_order: 1, step_index: 1, month: '02', community_key: '2', community_id: '2', member_count: 4, size_delta: 0, existing_count: 3, new_count: 1, lost_count: 1, reappearing_count: 0, members: ['u1', 'u2', 'u3', 'u5'], existing_members: ['u1', 'u2', 'u3'], new_members: ['u5'], lost_members: ['u4'], reappearing_members: [] },
    { path_id: 'path-1', display_order: 1, step_index: 2, month: '03', community_key: '3', community_id: '3', member_count: 5, size_delta: 1, existing_count: 4, new_count: 1, lost_count: 0, reappearing_count: 1, members: ['u1', 'u2', 'u3', 'u4', 'u5'], existing_members: ['u1', 'u2', 'u3', 'u5'], new_members: ['u4'], lost_members: [], reappearing_members: ['u4'] },
  ],
  'path-2': [
    { path_id: 'path-2', display_order: 2, step_index: 0, month: '02', community_key: '102', community_id: '102', member_count: 3, size_delta: null, existing_count: 3, new_count: 0, lost_count: 0, reappearing_count: 0, members: ['u7', 'u8', 'u9'], existing_members: ['u7', 'u8', 'u9'], new_members: [], lost_members: [], reappearing_members: [] },
    { path_id: 'path-2', display_order: 2, step_index: 1, month: '03', community_key: '103', community_id: '103', member_count: 3, size_delta: 0, existing_count: 2, new_count: 1, lost_count: 1, reappearing_count: 0, members: ['u7', 'u8', 'u10'], existing_members: ['u7', 'u8'], new_members: ['u10'], lost_members: ['u9'], reappearing_members: [] },
  ],
};

function similarity(pathId, themeType) {
  const path = paths.find((item) => item.path_id === pathId) ?? paths[0];
  const themeColumn = themeType === 'absolute' ? 'absolute_theme' : themeType === 'weighted' ? 'weighted_theme' : 'general_theme';
  const months = path.steps.map((step) => step.month);
  return {
    run_id: 'run-1', path_id: path.path_id, theme_type: themeType,
    months, communities: path.steps.map((step) => step.community_key), themes: path.steps.map((step) => step[themeColumn]),
    matrix: months.map((_, row) => months.map((__, col) => row === col ? 1 : 0.72)),
    embedding_provider: 'tei', embedding_model: 'sentence-transformers/paraphrase-MiniLM-L6-v2',
    embedding_model_revision: methodology.similarity_model_revision,
  };
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location-search">{location.search}</output>;
}

function renderPage(entry = '/evolution?run=run-1') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <CommunityEvolution />
      <LocationProbe />
    </MemoryRouter>,
  );
}

describe('Community Evolution page', () => {
  beforeEach(() => {
    useCommunityEvolutionData.mockImplementation((pathId, themeType) => ({
      selectedRunId: 'run-1',
      pathsQuery: query({ run_id: 'run-1', paths, total: paths.length, methodology }),
      mobilityQuery: query({ run_id: 'run-1', path_id: pathId ?? 'path-1', records: mobilityByPath[pathId] ?? mobilityByPath['path-1'] }),
      similarityQuery: query(similarity(pathId ?? 'path-1', themeType)),
    }));
  });

  it('presents run-level context before the all-path master view', async () => {
    renderPage();

    expect(screen.getByText('Persistent paths')).toBeInTheDocument();
    expect(screen.getByText('Longest path')).toBeInTheDocument();
    expect(screen.getByText('Average path Jaccard')).toBeInTheDocument();
    expect(screen.getByText('Timeline coverage')).toBeInTheDocument();
    expect(screen.queryByText('Selected path duration')).not.toBeInTheDocument();
    expect(screen.queryByText('Selected membership')).not.toBeInTheDocument();

    expect(screen.getByRole('button', { name: /Select Path 1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Select Path 2/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Inspect persistent path')).toHaveValue('path-1');
    await waitFor(() => expect(useCommunityEvolutionData).toHaveBeenCalledWith('path-1', 'general'));
  });

  it('keeps all three thesis subsections on one page with methodology and reappearing mobility', async () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Community Similarity over Time' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Member Mobility' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Thematic Similarity' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'How Community Evolution is calculated' })).toBeInTheDocument();
    expect(screen.getByText('Jaccard ≥ 0.50')).toBeInTheDocument();
    expect(screen.getAllByText('Reappeared').length).toBeGreaterThan(0);
    expect(screen.getByText('Selected path', { selector: 'p' })).toBeInTheDocument();
    await waitFor(() => expect(useCommunityEvolutionData).toHaveBeenCalledWith('path-1', 'general'));
  });

  it('uses the master timeline selection to update URL-backed downstream detail', async () => {
    renderPage('/evolution?run=run-1&path=path-1');

    fireEvent.click(screen.getByRole('button', { name: /Select Path 2/ }));

    await waitFor(() => expect(useCommunityEvolutionData).toHaveBeenCalledWith('path-2', 'general'));
    await waitFor(() => expect(screen.getByTestId('location-search')).toHaveTextContent('path=path-2'));
    expect(screen.getByLabelText('Inspect persistent path')).toHaveValue('path-2');
    expect(screen.getByRole('button', { name: /Select Path 2/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('C102', { selector: 'p' })).toBeInTheDocument();
    expect(screen.getAllByText(/Path 2 · 02 → 03/).length).toBeGreaterThan(0);
  });

  it('keeps the contextual dropdown synchronized with the selected timeline row', async () => {
    renderPage('/evolution?run=run-1&path=path-1');

    fireEvent.change(screen.getByLabelText('Inspect persistent path'), { target: { value: 'path-2' } });

    await waitFor(() => expect(useCommunityEvolutionData).toHaveBeenCalledWith('path-2', 'general'));
    expect(screen.getByRole('button', { name: /Select Path 2/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Select Path 1/ })).toHaveAttribute('aria-pressed', 'false');
    await waitFor(() => expect(screen.getByTestId('location-search')).toHaveTextContent('path=path-2'));
  });

  it('restores a direct path URL and deterministically repairs an invalid path', async () => {
    const direct = renderPage('/evolution?run=run-1&path=path-2');
    expect(screen.getByLabelText('Inspect persistent path')).toHaveValue('path-2');
    expect(screen.getByRole('button', { name: /Select Path 2/ })).toHaveAttribute('aria-pressed', 'true');
    direct.unmount();

    renderPage('/evolution?run=run-1&path=missing-path');
    await waitFor(() => expect(screen.getByTestId('location-search')).toHaveTextContent('path=path-1'));
    expect(screen.getByLabelText('Inspect persistent path')).toHaveValue('path-1');
    expect(screen.getByRole('button', { name: /Select Path 1/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('keeps theme perspective independent from the shared path selection', async () => {
    renderPage('/evolution?run=run-1&path=path-2');

    fireEvent.click(screen.getByRole('button', { name: 'IF' }));

    await waitFor(() => expect(useCommunityEvolutionData).toHaveBeenCalledWith('path-2', 'absolute'));
    expect(screen.getByLabelText('Inspect persistent path')).toHaveValue('path-2');
    await waitFor(() => {
      const search = screen.getByTestId('location-search').textContent ?? '';
      expect(search).toContain('path=path-2');
      expect(search).toContain('themeView=absolute');
    });
  });
});
