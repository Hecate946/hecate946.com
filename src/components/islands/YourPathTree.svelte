<script lang="ts">
  import { onMount } from 'svelte';
  import {
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type Simulation,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
  } from 'd3-force';

  interface PathEntry {
    path: string;
    at: string;
    session: string;
  }

  interface LocalVisitorStats {
    pathHistory?: PathEntry[];
  }

  interface PathNode extends SimulationNodeDatum {
    id: string;
    path: string;
    label: string;
    count: number;
    incoming: number;
    outgoing: number;
    meanOrder: number;
    radius: number;
    current: boolean;
    anchorX: number;
    anchorY: number;
  }

  interface PathEdge extends SimulationLinkDatum<PathNode> {
    id: string;
    source: string | PathNode;
    target: string | PathNode;
    sourceId: string;
    targetId: string;
    count: number;
    reciprocal: boolean;
  }

  interface PathGraphData {
    nodes: PathNode[];
    edges: PathEdge[];
    maxNodeCount: number;
    maxEdgeCount: number;
  }

  const LOCAL_STATS_KEY = 'hecate946:your-stats';
  const WIDTH = 1000;
  const HEIGHT = 440;
  const SIDE_PADDING = 105;
  const MAX_ENTRIES = 160;
  const ARROW_ID = 'your-path-arrow';

  let entries: PathEntry[] = [];
  let currentPath = '/';
  let graphNodes: PathNode[] = [];
  let graphEdges: PathEdge[] = [];
  let maxNodeCount = 1;
  let maxEdgeCount = 1;
  let hoveredNodeId = '';
  let simulation: Simulation<PathNode, undefined> | null = null;
  let mounted = false;

  $: hoveredNode = graphNodes.find((node) => node.id === hoveredNodeId) ?? null;

  function normalizePath(path: string) {
    if (!path || path === '/') return '/';
    return `/${path.replace(/^\/+|\/+$/g, '')}/`;
  }

  function labelForPath(path: string) {
    if (path === '/') return 'Home';
    const parts = path.split('/').filter(Boolean);
    const leaf = parts.at(-1) ?? 'Page';
    return leaf
      .replace(/[-_]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function stableUnit(value: string) {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return ((hash >>> 0) % 10_000) / 10_000;
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
      hoveredNodeId = '';
      rebuildGraph();
      window.dispatchEvent(new CustomEvent('hecate:local-stats-updated'));
    } catch {
      // Personal path data is optional; blocked storage should not break the page.
    }
  }

  function buildGraph(pathEntries: PathEntry[], activePath: string): PathGraphData {
    const nodeStats = new Map<
      string,
      { count: number; orderTotal: number; orderSamples: number; incoming: number; outgoing: number }
    >();
    const edgeCounts = new Map<string, number>();
    const sessions = new Map<string, PathEntry[]>();

    for (const entry of pathEntries) {
      const list = sessions.get(entry.session) ?? [];
      list.push(entry);
      sessions.set(entry.session, list);
    }

    for (const sessionEntries of sessions.values()) {
      const ordered = [...sessionEntries].sort(
        (first, second) => Date.parse(first.at) - Date.parse(second.at),
      );
      const cleanPaths: string[] = [];

      for (const entry of ordered) {
        const path = normalizePath(entry.path);
        if (cleanPaths.at(-1) !== path) cleanPaths.push(path);
      }

      const denominator = Math.max(1, cleanPaths.length - 1);
      cleanPaths.forEach((path, index) => {
        const stat = nodeStats.get(path) ?? {
          count: 0,
          orderTotal: 0,
          orderSamples: 0,
          incoming: 0,
          outgoing: 0,
        };
        stat.count += 1;
        stat.orderTotal += index / denominator;
        stat.orderSamples += 1;
        nodeStats.set(path, stat);
      });

      for (let index = 1; index < cleanPaths.length; index += 1) {
        const source = cleanPaths[index - 1];
        const target = cleanPaths[index];
        if (source === target) continue;
        const key = `${source}\u0000${target}`;
        edgeCounts.set(key, (edgeCounts.get(key) ?? 0) + 1);
        const sourceStat = nodeStats.get(source);
        const targetStat = nodeStats.get(target);
        if (sourceStat) sourceStat.outgoing += 1;
        if (targetStat) targetStat.incoming += 1;
      }
    }

    const maxCount = Math.max(1, ...Array.from(nodeStats.values(), (stat) => stat.count));
    const active = normalizePath(activePath);
    const nodes = Array.from(nodeStats.entries(), ([path, stat]) => {
      const meanOrder = stat.orderSamples > 0 ? stat.orderTotal / stat.orderSamples : 0.5;
      const relativeWeight = Math.sqrt(stat.count / maxCount);
      const radius = 20 + relativeWeight * 16;
      const lane = stableUnit(path) - 0.5;
      const anchorX = SIDE_PADDING + meanOrder * (WIDTH - SIDE_PADDING * 2);
      const anchorY = HEIGHT / 2 + lane * 150;
      const angle = stableUnit(`${path}:angle`) * Math.PI * 2;
      const spread = 45 + stableUnit(`${path}:spread`) * 75;

      return {
        id: path,
        path,
        label: labelForPath(path),
        count: stat.count,
        incoming: stat.incoming,
        outgoing: stat.outgoing,
        meanOrder,
        radius,
        current: path === active,
        anchorX,
        anchorY,
        x: anchorX + Math.cos(angle) * spread,
        y: anchorY + Math.sin(angle) * spread,
      } satisfies PathNode;
    });

    const edges = Array.from(edgeCounts.entries(), ([key, count]) => {
      const [sourceId, targetId] = key.split('\u0000');
      return {
        id: `${sourceId}->${targetId}`,
        source: sourceId,
        target: targetId,
        sourceId,
        targetId,
        count,
        reciprocal: edgeCounts.has(`${targetId}\u0000${sourceId}`),
      } satisfies PathEdge;
    });

    return {
      nodes,
      edges,
      maxNodeCount: maxCount,
      maxEdgeCount: Math.max(1, ...edges.map((edge) => edge.count)),
    };
  }

  function rebuildGraph() {
    simulation?.stop();
    const graph = buildGraph(entries, currentPath);
    graphNodes = graph.nodes;
    graphEdges = graph.edges;
    maxNodeCount = graph.maxNodeCount;
    maxEdgeCount = graph.maxEdgeCount;

    if (!mounted || graphNodes.length === 0) return;

    simulation = forceSimulation<PathNode>(graphNodes)
      .force(
        'link',
        forceLink<PathNode, PathEdge>(graphEdges)
          .id((node) => node.id)
          .distance((edge) => 128 - Math.min(34, Math.sqrt(edge.count) * 11))
          .strength((edge) => 0.13 + Math.min(0.18, edge.count * 0.035)),
      )
      .force('charge', forceManyBody<PathNode>().strength(-410))
      .force(
        'collision',
        forceCollide<PathNode>()
          .radius((node) => node.radius + 30)
          .strength(0.92)
          .iterations(2),
      )
      .force('x', forceX<PathNode>((node) => node.anchorX).strength(0.085))
      .force('y', forceY<PathNode>((node) => node.anchorY).strength(0.055))
      .alpha(0.95)
      .alphaDecay(0.035)
      .velocityDecay(0.36)
      .on('tick', () => {
        for (const node of graphNodes) {
          const margin = node.radius + 26;
          node.x = Math.min(WIDTH - margin, Math.max(margin, node.x ?? WIDTH / 2));
          node.y = Math.min(HEIGHT - margin - 18, Math.max(margin, node.y ?? HEIGHT / 2));
        }
        graphNodes = graphNodes;
        graphEdges = graphEdges;
      });
  }

  function endpointNode(endpoint: string | number | PathNode) {
    if (typeof endpoint === 'object') return endpoint;
    return graphNodes.find((node) => node.id === String(endpoint));
  }

  function edgePath(edge: PathEdge) {
    const source = endpointNode(edge.source);
    const target = endpointNode(edge.target);
    if (!source || !target) return '';

    const sx = source.x ?? source.anchorX;
    const sy = source.y ?? source.anchorY;
    const tx = target.x ?? target.anchorX;
    const ty = target.y ?? target.anchorY;
    const dx = tx - sx;
    const dy = ty - sy;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const ux = dx / distance;
    const uy = dy / distance;
    const startPadding = source.radius + 3;
    const endPadding = target.radius + 9;
    const startX = sx + ux * startPadding;
    const startY = sy + uy * startPadding;
    const endX = tx - ux * endPadding;
    const endY = ty - uy * endPadding;

    if (!edge.reciprocal) {
      return `M ${startX} ${startY} L ${endX} ${endY}`;
    }

    const curve = Math.min(52, distance * 0.17);
    const midX = (startX + endX) / 2 - uy * curve;
    const midY = (startY + endY) / 2 + ux * curve;
    return `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`;
  }

  function edgeWeight(edge: PathEdge) {
    return Math.sqrt(edge.count / maxEdgeCount);
  }

  function nodeWeight(node: PathNode) {
    return Math.sqrt(node.count / maxNodeCount);
  }

  function tooltipPosition(node: PathNode) {
    const x = ((node.x ?? node.anchorX) / WIDTH) * 100;
    const y = ((node.y ?? node.anchorY) / HEIGHT) * 100;
    return `left:${x}%;top:${y}%;--node-radius:${node.radius}px`;
  }

  onMount(() => {
    mounted = true;
    currentPath = window.location.pathname;
    readEntries();

    const handleUpdate = () => {
      currentPath = window.location.pathname;
      readEntries();
    };

    window.addEventListener('hecate:local-stats-updated', handleUpdate);
    window.addEventListener('storage', handleUpdate);
    document.addEventListener('astro:page-load', handleUpdate);

    return () => {
      mounted = false;
      simulation?.stop();
      window.removeEventListener('hecate:local-stats-updated', handleUpdate);
      window.removeEventListener('storage', handleUpdate);
      document.removeEventListener('astro:page-load', handleUpdate);
    };
  });
</script>

<div class="path-graph-shell">
  <button class="path-clear" type="button" on:click={clearLocalData} aria-label="Clear my path data">
    Clear
  </button>

  {#if graphNodes.length > 0}
    <svg
      class="path-graph"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Directed weighted graph of this browser's navigation path"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <marker
          id={ARROW_ID}
          viewBox="0 0 7 7"
          refX="6.2"
          refY="3.5"
          markerWidth="8"
          markerHeight="8"
          markerUnits="userSpaceOnUse"
          orient="auto"
        >
          <path class="path-graph__arrow" d="M0 0 7 3.5 0 7Z" />
        </marker>
      </defs>

      <g class="path-graph__edges" aria-hidden="true">
        {#each graphEdges as edge (edge.id)}
          <path
            d={edgePath(edge)}
            marker-end={`url(#${ARROW_ID})`}
            style={`--edge-weight:${edgeWeight(edge)}`}
          />
        {/each}
      </g>

      <g class="path-graph__nodes">
        {#each graphNodes as node (node.id)}
          <a
            class="path-graph__node"
            class:path-graph__node--current={node.current}
            href={node.path}
            aria-label={`${node.label}: ${node.count} ${node.count === 1 ? 'visit' : 'visits'}`}
            on:mouseenter={() => (hoveredNodeId = node.id)}
            on:mouseleave={() => (hoveredNodeId = '')}
            on:focus={() => (hoveredNodeId = node.id)}
            on:blur={() => (hoveredNodeId = '')}
            transform={`translate(${node.x ?? node.anchorX} ${node.y ?? node.anchorY})`}
            style={`--node-weight:${nodeWeight(node)}`}
          >
            <circle r={node.radius} />
            <text class="path-graph__count" dy="0.34em">{node.count}</text>
            <text class="path-graph__label" y={node.radius + 19}>{node.label}</text>
          </a>
        {/each}
      </g>
    </svg>

    {#if hoveredNode}
      <div class="path-graph-tooltip" style={tooltipPosition(hoveredNode)} aria-hidden="true">
        <strong>{hoveredNode.label}</strong>
        <span>
          {hoveredNode.count} {hoveredNode.count === 1 ? 'visit' : 'visits'} · {hoveredNode.incoming} in · {hoveredNode.outgoing} out
        </span>
      </div>
    {/if}
  {:else}
    <div class="path-graph-empty">No path yet.</div>
  {/if}
</div>
