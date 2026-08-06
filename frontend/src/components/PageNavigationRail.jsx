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
  Users
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
  provenance: FileText
};

export default function PageNavigationRail({ sections, containerId = "main-content" }) {
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

        if (mostVisible) {
          setActiveSection(mostVisible);
        }
      },
      {
        root: container,
        rootMargin: '-10% 0px -40% 0px',
        threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
      }
    );

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections, containerId]);

  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    const container = document.getElementById(containerId);
    
    if (el && container) {
      const containerRect = container.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      
      container.scrollTo({
        top: container.scrollTop + (elRect.top - containerRect.top) - 20,
        behavior: 'smooth'
      });
      setActiveSection(id);
    }
  };

  if (!sections || sections.length === 0) return null;

  return (
    <div className="pointer-events-auto flex flex-col bg-surface/80 backdrop-blur-md border border-border/60 rounded-2xl p-1.5 sm:p-2 shadow-lg animate-fade-in-up">
      {sections.map(({ id, label, icon: iconName }) => {
        const Icon = SECTION_ICONS[iconName] || List;
        const isActive = activeSection === id;
        
        return (
          <button
            key={id}
            onClick={() => scrollToSection(id)}
            title={label}
            className={`group relative p-2 sm:p-3 rounded-xl transition-all duration-300 mb-1 sm:mb-2 last:mb-0
              ${isActive ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-surface-soft hover:text-text-heading'}
            `}
            aria-label={label}
            aria-current={isActive ? 'true' : undefined}
          >
            <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className={`absolute right-full mr-4 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg bg-surface border border-border/60 text-sm font-semibold text-text shadow-md whitespace-nowrap opacity-0 pointer-events-none transition-all duration-300 transform group-hover:opacity-100 group-hover:translate-x-0 ${isActive ? 'translate-x-0 opacity-0' : 'translate-x-4'}`}>
              {label}
            </span>
            {isActive && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-md" />
            )}
          </button>
        );
      })}
    </div>
  );
}
