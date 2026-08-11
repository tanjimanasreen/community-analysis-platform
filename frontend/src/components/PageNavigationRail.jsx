import React, { useEffect, useState } from 'react';
import {
  Activity,
  BarChart2,
  Network,
  List,
  Hash,
  Clock,
  Database,
  FileText,
  Users,
} from 'lucide-react';

export const SECTION_ICONS = {
  kpis: BarChart2,
  trends: Activity,
  network: Network,
  actors: Users,
  themes: Hash,
  continuity: Clock,
  communities: List,
  metadata: Database,
  provenance: FileText,
};

export function PageNavigationRailSlot({
  sections,
  containerId = 'main-content',
  className = 'md:block lg:ml-6',
}) {
  if (!sections || sections.length === 0) return null;
  return (
    <aside
      className={`pointer-events-none sticky top-4 z-40 ml-4 hidden w-14 shrink-0 self-start ${className}`}
      aria-label="Page section navigation"
    >
      <div className="pointer-events-auto">
        <PageNavigationRail sections={sections} containerId={containerId} />
      </div>
    </aside>
  );
}

export default function PageNavigationRail({ sections, containerId = 'main-content' }) {
  const [activeSection, setActiveSection] = useState(sections[0]?.id);

  useEffect(() => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let maxRatio = 0;
        let mostVisible = null;

        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            mostVisible = entry.target.id;
          }
        });

        if (mostVisible) setActiveSection(mostVisible);
      },
      {
        root: container,
        rootMargin: '-10% 0px -40% 0px',
        threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
      },
    );

    sections.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [sections, containerId]);

  const scrollToSection = (id) => {
    const element = document.getElementById(id);
    const container = document.getElementById(containerId);

    if (element && container) {
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();

      container.scrollTo({
        top: container.scrollTop + (elementRect.top - containerRect.top) - 20,
        behavior: 'smooth',
      });
      setActiveSection(id);
      if (typeof element.focus === 'function' && element.hasAttribute('tabindex')) {
        window.requestAnimationFrame(() => element.focus({ preventScroll: true }));
      }
    }
  };

  if (!sections || sections.length === 0) return null;

  return (
    <nav
      aria-label="Section rail"
      className="flex flex-col gap-1 rounded-2xl border border-border/60 bg-surface/80 p-1.5 shadow-lg backdrop-blur-md sm:p-2 animate-fade-in-up"
    >
      {sections.map(({ id, label, icon: iconName }) => {
        const Icon = SECTION_ICONS[iconName] || List;
        const isActive = activeSection === id;

        return (
          <button
            key={id}
            type="button"
            onClick={() => scrollToSection(id)}
            title={label}
            className={`group relative rounded-xl p-2 transition-all duration-300 sm:p-2.5
              ${isActive ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-surface-soft hover:text-text-heading'}
            `}
            aria-label={label}
            aria-current={isActive ? 'true' : undefined}
          >
            <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
            <span className={`pointer-events-none absolute right-full top-1/2 mr-4 -translate-y-1/2 whitespace-nowrap rounded-lg border border-border/60 bg-surface px-3 py-1.5 text-sm font-semibold text-text opacity-0 shadow-md transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100 ${isActive ? 'translate-x-0 opacity-0' : 'translate-x-4'}`}>
              {label}
            </span>
            {isActive && (
              <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-md bg-primary" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
