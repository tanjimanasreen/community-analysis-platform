import React from 'react';
import { Activity, GitCompareArrows, MessageSquare, Network, ShieldCheck, Users } from 'lucide-react';
import MetricCard from './MetricCard';
import { formatCount, metricCommunityCount } from '../features/overview/overviewUtils';

export default function KPICards({ overview, metric }) {
  const communityCount = metricCommunityCount(overview, metric);
  const matchedDetail = overview.matched_percentage === null
    ? 'Matched percentage unavailable'
    : `${formatCount(overview.matched_percentage)}% of the larger IF/WIF partition`;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <MetricCard
        title="Total Users"
        value={overview.total_users}
        source="overview.total_users"
        icon={Users}
        colorClass="text-primary"
        bgClass="bg-primary"
        format={formatCount}
      />
      <MetricCard
        title="Total Messages"
        value={overview.total_messages}
        source="overview.total_messages"
        icon={MessageSquare}
        colorClass="text-secondary"
        bgClass="bg-secondary"
        format={formatCount}
      />
      <MetricCard
        title="Total Interactions"
        value={overview.total_interactions}
        source="overview.total_interactions"
        icon={Activity}
        colorClass="text-success"
        bgClass="bg-success"
        format={formatCount}
      />
      <MetricCard
        title={`${metric.toUpperCase()} Communities`}
        value={communityCount}
        detail={metric === 'if' ? 'Interaction Frequency partition' : 'Weighted Interaction Frequency partition'}
        source={metric === 'if' ? 'overview.if_community_count' : 'overview.wif_community_count'}
        icon={Network}
        colorClass="text-warning"
        bgClass="bg-warning"
        format={formatCount}
      />
      <MetricCard
        title="Matched Communities"
        value={overview.matched_community_count}
        detail={matchedDetail}
        source="overview.matched_community_count and overview.matched_percentage"
        icon={GitCompareArrows}
        colorClass="text-primary"
        bgClass="bg-primary"
        format={formatCount}
      />
      <MetricCard
        title="Persistent Communities"
        value={overview.persistent_community_count}
        detail="Available only when longitudinal transitions were generated"
        source="overview.persistent_community_count"
        icon={ShieldCheck}
        colorClass="text-secondary"
        bgClass="bg-secondary"
        format={formatCount}
      />
    </div>
  );
}
