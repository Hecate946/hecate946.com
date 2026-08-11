<script lang="ts">
  import { onMount } from 'svelte';
  import ForceNetwork from '@/components/graphs/ForceNetwork.svelte';
  import type { NetworkLink, NetworkNode } from '@/components/graphs/types';
  import {
    navigationNetworkNodes,
    navigationRainbowAccent,
  } from '@/data/navigation-network';

  interface PathEntry {
    path: string;
    at: string;
    session: string;
  }

  interface LocalVisitorStats {
    pathHistory?: PathEntry[];
  }

  const LOCAL_STATS_KEY = 'hecate946:your-stats';
  const MAX_ENTRIES = 200;

  let entries: PathEntry[] = [];
  let graphNodes: NetworkNode[] = [];
  let graphLinks: NetworkLink[] = [];

  const pathByNodeId = new Map(
    navigationNetworkNodes.map((node) => [
      node.id,
      canonicalPath(pathFromHref(node.href ?? '/')),
    ]),
  );
  function pathFromHref(href: string) {
    try {
      return new URL(href, 'https://hecate.local').pathname;
    } catch {
      return href.startsWith('/') ? href : '/';
    }
  }

  function canonicalPath(path: string) {
    const raw = String(path || '/').split('?')[0].split('#')[0] || '/';
    let normalized = raw.startsWith('/') ? raw : `/${raw}`;
    normalized = normalized.replace(/\/index\.html$/i, '/').replace(/\/+$/, '');
    return normalized || '/';
  }

  /** Collapse the browser trail to the same six primary destinations + Home. */
  function primaryNodeId(path: string) {
    const normalized = canonicalPath(path);
    if (normalized === '/') return 'home';

    for (const [id, route] of pathByNodeId) {
      if (id === 'home') continue;
      if (normalized === route || normalized.startsWith(`${route}/`)) return id;
    }

    return null;
  }

  function readEntries() {
    try {
      const raw = window.localStorage.getItem(LOCAL_STATS_KEY);
      if (!raw) {
        entries = [];
      } else {
        const parsed = JSON.parse(raw) as LocalVisitorStats;
        entries = Array.isArray(parsed.pathHistory)
          ? parsed.pathHistory
              .filter(
                (entry): entry is PathEntry =>
                  Boolean(entry) &&
                  typeof entry.path === 'string' &&
                  typeof entry.at === 'string' &&
                  typeof entry.session === 'string',
              )
              .slice(-MAX_ENTRIES)
          : [];
      }
    } catch {
      entries = [];
    }

    rebuildGraph();
  }

  function clearLocalData() {
    try {
      window.localStorage.removeItem(LOCAL_STATS_KEY);
      entries = [];
      rebuildGraph();
      window.dispatchEvent(new CustomEvent('hecate:local-stats-updated'));
    } catch {
      // Personal path data is optional; blocked storage should not break Stats.
    }
  }

  function rebuildGraph() {
    const visitCounts = new Map(navigationNetworkNodes.map((node) => [node.id, 0]));
    const edgeCounts = new Map<string, number>();
    const sessions = new Map<string, PathEntry[]>();

    for (const entry of entries) {
      const list = sessions.get(entry.session) ?? [];
      list.push(entry);
      sessions.set(entry.session, list);
    }

    for (const sessionEntries of sessions.values()) {
      const ordered = [...sessionEntries].sort(
        (first, second) => Date.parse(first.at) - Date.parse(second.at),
      );
      const routeIds: string[] = [];

      for (const entry of ordered) {
        const id = primaryNodeId(entry.path);
        if (!id) continue;
        if (routeIds.at(-1) !== id) routeIds.push(id);
      }

      for (const id of routeIds) {
        visitCounts.set(id, (visitCounts.get(id) ?? 0) + 1);
      }

      for (let index = 1; index < routeIds.length; index += 1) {
        const source = routeIds[index - 1];
        const target = routeIds[index];
        if (source === target) continue;
        const key = `${source}\u0000${target}`;
        edgeCounts.set(key, (edgeCounts.get(key) ?? 0) + 1);
      }
    }

    const maxVisits = Math.max(1, ...visitCounts.values());
    const visitedNodeIds = new Set(
      Array.from(visitCounts.entries())
        .filter(([, count]) => count > 0)
        .map(([id]) => id),
    );

    graphNodes = navigationNetworkNodes
      .filter((node) => visitedNodeIds.has(node.id))
      .map((node) => {
        const visits = visitCounts.get(node.id) ?? 0;
        const relative = Math.sqrt(visits / maxVisits);
        return {
          ...node,
          accent: navigationRainbowAccent(node.id, node.accent),
          radius: node.id === 'home' ? 52 + relative * 7 : 29 + relative * 10,
          description: `${visits} ${visits === 1 ? 'visit' : 'visits'}`,
          descriptionAlwaysVisible: true,
          current: false,
        };
      });

    const maxTransitions = Math.max(1, ...edgeCounts.values());
    graphLinks = Array.from(edgeCounts.entries(), ([key, count]) => {
      const [source, target] = key.split('\u0000');
      const reverseKey = `${target}\u0000${source}`;
      const reciprocal = edgeCounts.has(reverseKey);
      const normalizedWeight = Math.sqrt(count / maxTransitions);

      // Every personal transition is a directed arc: no straight connector
      // bars. Reciprocal transitions intentionally share the same curve sign.
      // Because reversing source/target also reverses the path normal, the two
      // arrows then bow to opposite sides of the pair, visually like `( )`.
      const curve = reciprocal ? 54 : 40;

      return {
        source,
        target,
        kind: 'primary',
        directed: true,
        weight: normalizedWeight,
        curve,
        distance: 205 - normalizedWeight * 16,
        strength: 0.09 + normalizedWeight * 0.08,
      } satisfies NetworkLink;
    }).filter(
      (link) =>
        visitedNodeIds.has(String(link.source)) &&
        visitedNodeIds.has(String(link.target)),
    );
  }

  onMount(() => {
    readEntries();

    const handleUpdate = () => {
      readEntries();
    };

    window.addEventListener('hecate:local-stats-updated', handleUpdate);
    window.addEventListener('storage', handleUpdate);
    document.addEventListener('astro:page-load', handleUpdate);

    return () => {
      window.removeEventListener('hecate:local-stats-updated', handleUpdate);
      window.removeEventListener('storage', handleUpdate);
      document.removeEventListener('astro:page-load', handleUpdate);
    };
  });
</script>

<div class="path-force-shell">
  <button class="path-clear" type="button" on:click={clearLocalData} aria-label="Clear my path data">
    Clear
  </button>

  <div class="network-force-stage path-force-stage">
    <ForceNetwork
      nodes={graphNodes}
      links={graphLinks}
      centerNodeId="home"
      idPrefix="stats-personal-path"
      ariaLabel="Directed weighted graph of this browser's navigation among the primary pages"
      height="min(52svh, 32rem)"
      showHint={false}
      collisionSounds={false}
      settings={{
        layout: 'radial',
        radialRadius: 0.41,
        radialStartAngle: -Math.PI / 2,
        entranceRadius: 0,
        chargeStrength: -315,
        centerChargeMultiplier: 1.7,
        anchorStrength: 0.13,
        centerAnchorStrength: 0.28,
        collisionPadding: 28,
        linkStrength: 0.12,
      }}
    />
  </div>
</div>
