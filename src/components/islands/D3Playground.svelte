<script lang="ts">
  import { onMount } from 'svelte';
  import {
    forceCenter,
    forceCollide,
    forceLink,
    forceManyBody,
    forceRadial,
    forceSimulation,
    forceX,
    forceY,
    type Simulation,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
  } from 'd3-force';

  type SceneId =
    | 'living'
    | 'morph'
    | 'gravity'
    | 'hulls'
    | 'cascade'
    | 'collisions'
    | 'trails'
    | 'pathfinder';

  type LayoutMode = 'organic' | 'orbit' | 'grid' | 'split' | 'timeline';
  type PointerMode = 'attract' | 'repel';

  type GraphNode = SimulationNodeDatum & {
    id: string;
    label: string;
    group: number;
    radius: number;
    importance: number;
    born: number;
    trail: Array<{ x: number; y: number }>;
  };

  type GraphLink = SimulationLinkDatum<GraphNode> & {
    source: string | GraphNode;
    target: string | GraphNode;
    weight: number;
  };

  type GravityWell = {
    id: number;
    x: number;
    y: number;
    strength: number;
    phase: number;
  };

  type ThemeColors = {
    bg: string;
    surface: string;
    text: string;
    muted: string;
    line: string;
    accent: string;
    accentStrong: string;
    accentSoft: string;
    season: string[];
  };

  type DragState =
    | {
        kind: 'node';
        pointerId: number;
        node: GraphNode;
        moved: boolean;
        startX: number;
        startY: number;
      }
    | {
        kind: 'well';
        pointerId: number;
        well: GravityWell;
        moved: boolean;
        startX: number;
        startY: number;
      }
    | {
        kind: 'pan';
        pointerId: number;
        startX: number;
        startY: number;
        originX: number;
        originY: number;
        moved: boolean;
      }
    | {
        kind: 'lasso';
        pointerId: number;
        startX: number;
        startY: number;
        endX: number;
        endY: number;
      };

  const scenes: Array<{ id: SceneId; label: string; description: string; hint: string }> = [
    {
      id: 'living',
      label: 'Living graph',
      description: 'Zoomable network with semantic labels, neighbor focus, animated edge traffic, dragging, and group selection.',
      hint: 'Hover a node, drag it, scroll to zoom, or Shift-drag to select a group.',
    },
    {
      id: 'morph',
      label: 'Layout morph',
      description: 'The same data smoothly reorganizes between organic, orbital, grid, split, and timeline layouts.',
      hint: 'Switch layouts while the simulation is moving—the graph never hard-cuts.',
    },
    {
      id: 'gravity',
      label: 'Gravity painter',
      description: 'Paint custom attractors into the force field and watch particles bend into unstable orbital systems.',
      hint: 'Click empty space to add a gravity well. Drag wells to reposition them.',
    },
    {
      id: 'hulls',
      label: 'Community hulls',
      description: 'Animated convex hulls wrap communities while the nodes continuously negotiate space.',
      hint: 'Click a community hull to pull that group forward; click again to release it.',
    },
    {
      id: 'cascade',
      label: 'Signal cascade',
      description: 'A breadth-first wave travels through the network with timed node and edge pulses.',
      hint: 'Click any node to launch a signal through the graph.',
    },
    {
      id: 'collisions',
      label: 'Collision field',
      description: 'Variable-radius bodies collide while the pointer acts as an attraction or repulsion field.',
      hint: 'Move through the field, switch polarity, and click empty space to spawn bodies.',
    },
    {
      id: 'trails',
      label: 'Memory trails',
      description: 'Force-driven particles retain fading histories, turning graph physics into generative drawing.',
      hint: 'Drag through the system or trigger an explosion to redraw the composition.',
    },
    {
      id: 'pathfinder',
      label: 'Pathfinder',
      description: 'Choose two nodes and animate the shortest route while unrelated structure fades away.',
      hint: 'Click a start node, then an end node. Click a third node to begin again.',
    },
  ];

  let canvas!: HTMLCanvasElement;
  let shell!: HTMLDivElement;
  let context: CanvasRenderingContext2D | null = null;
  let simulation: Simulation<GraphNode, GraphLink> | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let themeObserver: MutationObserver | null = null;
  let reducedMotionQuery: MediaQueryList | null = null;
  let animationFrame = 0;
  let lastFrame = 0;
  let width = 960;
  let height = 620;
  let dpr = 1;
  let nodes: GraphNode[] = [];
  let links: GraphLink[] = [];
  let wells: GravityWell[] = [];
  let activeScene: SceneId = 'living';
  let layoutMode: LayoutMode = 'organic';
  let pointerMode: PointerMode = 'attract';
  let paused = false;
  let reducedMotion = false;
  let labelsVisible = true;
  let hoverNode: GraphNode | null = null;
  let focusedNode: GraphNode | null = null;
  let activeCommunity: number | null = null;
  let selectedIds = new Set<string>();
  let dragState: DragState | null = null;
  let pointer = { x: -10_000, y: -10_000, inside: false };
  let zoom = { x: 0, y: 0, k: 1 };
  let pulseStart = 0;
  let pulseDistances = new Map<string, number>();
  let pulseEdgeDistances = new Map<string, number>();
  let pathStart: GraphNode | null = null;
  let pathEnd: GraphNode | null = null;
  let pathIds = new Set<string>();
  let pathEdgeIds = new Set<string>();
  let wellSequence = 0;
  let seed = 946;
  let status = scenes[0].hint;
  let colors: ThemeColors = {
    bg: '#fff8e8',
    surface: '#fffdf5',
    text: '#173d3b',
    muted: '#607874',
    line: 'rgba(24, 92, 87, .2)',
    accent: '#0f7773',
    accentStrong: '#07524f',
    accentSoft: 'rgba(15, 119, 115, .13)',
    season: ['#1b8c81', '#f2b84a', '#ef7766'],
  };

  const currentScene = () => scenes.find((scene) => scene.id === activeScene) ?? scenes[0];
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
  const nodeX = (node: GraphNode) => node.x ?? width / 2;
  const nodeY = (node: GraphNode) => node.y ?? height / 2;
  const sourceNode = (link: GraphLink) =>
    typeof link.source === 'string' ? nodes.find((node) => node.id === link.source)! : link.source;
  const targetNode = (link: GraphLink) =>
    typeof link.target === 'string' ? nodes.find((node) => node.id === link.target)! : link.target;
  const linkKey = (source: GraphNode, target: GraphNode) =>
    source.id < target.id ? `${source.id}|${target.id}` : `${target.id}|${source.id}`;

  function randomFactory(value: number) {
    let state = value >>> 0;
    return () => {
      state += 0x6d2b79f5;
      let next = state;
      next = Math.imul(next ^ (next >>> 15), next | 1);
      next ^= next + Math.imul(next ^ (next >>> 7), next | 61);
      return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeNetwork(nodeCount = 34, groupCount = 4, linkCount = 58) {
    const random = randomFactory(seed + activeScene.length * 31);
    const nextNodes: GraphNode[] = Array.from({ length: nodeCount }, (_, index) => ({
      id: `n${index}`,
      label: ['Archive', 'Rhythm', 'Atlas', 'Signal', 'Orbit', 'Memory', 'Bridge', 'Pulse'][index % 8] + ` ${index + 1}`,
      group: index % groupCount,
      radius: 7 + random() * 8 + (index < groupCount ? 5 : 0),
      importance: index < groupCount ? 1 : random(),
      born: index,
      trail: [],
      x: width / 2 + (random() - 0.5) * 120,
      y: height / 2 + (random() - 0.5) * 120,
    }));

    const keys = new Set<string>();
    const nextLinks: GraphLink[] = [];

    const addLink = (a: number, b: number, weight = 1) => {
      if (a === b) return;
      const source = nextNodes[a];
      const target = nextNodes[b];
      const key = linkKey(source, target);
      if (keys.has(key)) return;
      keys.add(key);
      nextLinks.push({ source: source.id, target: target.id, weight });
    };

    for (let index = 0; index < nodeCount; index += 1) {
      addLink(index, (index + groupCount) % nodeCount, 1.15);
      if (index >= groupCount) addLink(index, index % groupCount, 1.35);
    }

    while (nextLinks.length < linkCount) {
      const sourceIndex = Math.floor(random() * nodeCount);
      const sameGroup = random() < 0.68;
      const candidates = nextNodes.filter(
        (node, index) => index !== sourceIndex && (!sameGroup || node.group === nextNodes[sourceIndex].group),
      );
      const target = candidates[Math.floor(random() * candidates.length)];
      addLink(sourceIndex, nextNodes.indexOf(target), 0.65 + random() * 0.8);
    }

    return { nodes: nextNodes, links: nextLinks };
  }

  function makeCollisionField(count = 52) {
    const random = randomFactory(seed + 712);
    return {
      nodes: Array.from({ length: count }, (_, index): GraphNode => ({
        id: `b${index}`,
        label: `Body ${index + 1}`,
        group: index % 4,
        radius: 6 + Math.pow(random(), 1.8) * 24,
        importance: random(),
        born: index,
        trail: [],
        x: random() * width,
        y: random() * height,
        vx: (random() - 0.5) * 4,
        vy: (random() - 0.5) * 4,
      })),
      links: [] as GraphLink[],
    };
  }

  function makeGravityField(count = 62) {
    const random = randomFactory(seed + 218);
    return {
      nodes: Array.from({ length: count }, (_, index): GraphNode => ({
        id: `p${index}`,
        label: `Particle ${index + 1}`,
        group: index % 3,
        radius: 3.5 + random() * 4.5,
        importance: random(),
        born: index,
        trail: [],
        x: random() * width,
        y: random() * height,
        vx: (random() - 0.5) * 2,
        vy: (random() - 0.5) * 2,
      })),
      links: [] as GraphLink[],
    };
  }

  function resetScene(nextSeed = false) {
    if (nextSeed) seed += 1;
    simulation?.stop();
    hoverNode = null;
    focusedNode = null;
    selectedIds = new Set();
    activeCommunity = null;
    dragState = null;
    pointer = { x: -10_000, y: -10_000, inside: false };
    zoom = { x: 0, y: 0, k: 1 };
    pulseDistances = new Map();
    pulseEdgeDistances = new Map();
    pathStart = null;
    pathEnd = null;
    pathIds = new Set();
    pathEdgeIds = new Set();
    pulseStart = 0;
    wells = [];
    layoutMode = 'organic';

    const data =
      activeScene === 'collisions'
        ? makeCollisionField()
        : activeScene === 'gravity' || activeScene === 'trails'
          ? makeGravityField(activeScene === 'trails' ? 46 : 62)
          : makeNetwork(activeScene === 'hulls' ? 42 : 34, activeScene === 'hulls' ? 4 : 4, activeScene === 'hulls' ? 72 : 58);

    nodes = data.nodes;
    links = data.links;

    if (activeScene === 'gravity') {
      wells = [
        { id: ++wellSequence, x: width * 0.36, y: height * 0.5, strength: 0.085, phase: 0 },
        { id: ++wellSequence, x: width * 0.67, y: height * 0.47, strength: 0.065, phase: Math.PI },
      ];
    }

    buildSimulation();
    status = currentScene().hint;
  }

  function buildSimulation() {
    simulation?.stop();
    const nextSimulation = forceSimulation<GraphNode, GraphLink>(nodes)
      .alphaDecay(0.025)
      .velocityDecay(activeScene === 'gravity' || activeScene === 'trails' ? 0.08 : 0.34)
      .on('tick', ticked);
    simulation = nextSimulation;

    configureForces();

    if (reducedMotion || paused) {
      nextSimulation.stop();
      const tickCount = reducedMotion ? 260 : 180;
      for (let index = 0; index < tickCount; index += 1) nextSimulation.tick();
      ticked();
    } else {
      nextSimulation.alpha(0.9).restart();
    }
  }

  function configureForces() {
    if (!simulation) return;

    simulation
      .force('link', null)
      .force('charge', null)
      .force('center', null)
      .force('x', null)
      .force('y', null)
      .force('radial', null)
      .force('collision', null)
      .force('scene', null)
      .force('pointer', null);

    if (activeScene === 'gravity' || activeScene === 'trails') {
      simulation
        .velocityDecay(activeScene === 'trails' ? 0.12 : 0.065)
        .force('center', forceCenter(width / 2, height / 2).strength(0.008))
        .force('collision', forceCollide<GraphNode>().radius((node: GraphNode) => node.radius + 1).strength(0.35))
        .force('scene', gravityForce());
      return;
    }

    if (activeScene === 'collisions') {
      simulation
        .velocityDecay(0.025)
        .force('center', forceCenter(width / 2, height / 2).strength(0.002))
        .force('collision', forceCollide<GraphNode>().radius((node: GraphNode) => node.radius + 1.5).strength(1).iterations(2))
        .force('pointer', pointerForce())
        .force('scene', boundaryForce());
      return;
    }

    const distance = activeScene === 'hulls' ? 56 : 72;
    const charge = activeScene === 'hulls' ? -115 : -150;

    simulation
      .velocityDecay(0.34)
      .force(
        'link',
        forceLink<GraphNode, GraphLink>(links)
          .id((node: GraphNode) => node.id)
          .distance((link: GraphLink) => distance + (1.4 - link.weight) * 18)
          .strength((link: GraphLink) => 0.08 + link.weight * 0.08),
      )
      .force('charge', forceManyBody<GraphNode>().strength(charge))
      .force('collision', forceCollide<GraphNode>().radius((node: GraphNode) => node.radius + 9).strength(0.9))
      .force('center', forceCenter(width / 2, height / 2).strength(0.04));

    if (activeScene === 'hulls') {
      applyCommunityForces();
    } else if (activeScene === 'morph') {
      applyLayoutForces();
    }
  }

  function gravityForce() {
    let forceNodes: GraphNode[] = nodes;

    const force = (alpha: number) => {
      const time = performance.now() * 0.00035;
      for (const node of forceNodes) {
        let ax = 0;
        let ay = 0;

        if (activeScene === 'gravity') {
          for (const well of wells) {
            const dx = well.x - nodeX(node);
            const dy = well.y - nodeY(node);
            const distanceSquared = Math.max(900, dx * dx + dy * dy);
            const distance = Math.sqrt(distanceSquared);
            const pull = (well.strength * 3800) / distanceSquared;
            ax += dx * pull;
            ay += dy * pull;
            const tangent = 0.0018 * Math.sin(time + well.phase + node.born * 0.17);
            ax += -dy * tangent;
            ay += dx * tangent;
          }
        } else {
          const angle = node.born * 2.3999632297 + time * (0.35 + (node.group % 3) * 0.1);
          const targetRadius = Math.min(width, height) * (0.16 + (node.born % 11) / 42);
          const targetX = width / 2 + Math.cos(angle) * targetRadius;
          const targetY = height / 2 + Math.sin(angle * 1.12) * targetRadius * 0.72;
          ax += (targetX - nodeX(node)) * 0.0028;
          ay += (targetY - nodeY(node)) * 0.0028;
        }

        node.vx = (node.vx ?? 0) + ax * alpha;
        node.vy = (node.vy ?? 0) + ay * alpha;
      }
    };

    force.initialize = (nextNodes: GraphNode[]) => {
      forceNodes = nextNodes;
    };

    return force;
  }

  function pointerForce() {
    let forceNodes: GraphNode[] = nodes;

    const force = (alpha: number) => {
      if (!pointer.inside) return;
      const graphPointer = screenToGraph(pointer.x, pointer.y);
      for (const node of forceNodes) {
        const dx = graphPointer.x - nodeX(node);
        const dy = graphPointer.y - nodeY(node);
        const distanceSquared = Math.max(500, dx * dx + dy * dy);
        if (distanceSquared > 48_000) continue;
        const direction = pointerMode === 'attract' ? 1 : -1;
        const strength = (direction * 5200 * alpha) / distanceSquared;
        node.vx = (node.vx ?? 0) + dx * strength;
        node.vy = (node.vy ?? 0) + dy * strength;
      }
    };

    force.initialize = (nextNodes: GraphNode[]) => {
      forceNodes = nextNodes;
    };

    return force;
  }

  function boundaryForce() {
    let forceNodes: GraphNode[] = nodes;

    const force = () => {
      for (const node of forceNodes) {
        const x = nodeX(node);
        const y = nodeY(node);
        if (x < node.radius) node.vx = Math.abs(node.vx ?? 0) + 0.4;
        if (x > width - node.radius) node.vx = -Math.abs(node.vx ?? 0) - 0.4;
        if (y < node.radius) node.vy = Math.abs(node.vy ?? 0) + 0.4;
        if (y > height - node.radius) node.vy = -Math.abs(node.vy ?? 0) - 0.4;
      }
    };

    force.initialize = (nextNodes: GraphNode[]) => {
      forceNodes = nextNodes;
    };

    return force;
  }

  function applyLayoutForces() {
    if (!simulation) return;

    simulation.force('x', null).force('y', null).force('radial', null);

    if (layoutMode === 'organic') {
      simulation.force('center', forceCenter(width / 2, height / 2).strength(0.05));
      return;
    }

    if (layoutMode === 'orbit') {
      simulation
        .force('center', forceCenter(width / 2, height / 2).strength(0.018))
        .force(
          'radial',
          forceRadial<GraphNode>(
            (node) => Math.min(width, height) * (0.15 + node.group * 0.085),
            width / 2,
            height / 2,
          ).strength(0.62),
        );
      return;
    }

    if (layoutMode === 'grid') {
      const columns = Math.ceil(Math.sqrt(nodes.length * (width / height)));
      const rows = Math.ceil(nodes.length / columns);
      const cellWidth = width / (columns + 1);
      const cellHeight = height / (rows + 1);
      simulation
        .force('center', null)
        .force('x', forceX<GraphNode>((node) => cellWidth * ((node.born % columns) + 1)).strength(0.72))
        .force('y', forceY<GraphNode>((node) => cellHeight * (Math.floor(node.born / columns) + 1)).strength(0.72));
      return;
    }

    if (layoutMode === 'split') {
      const centers = [0.17, 0.39, 0.61, 0.83];
      simulation
        .force('center', null)
        .force('x', forceX<GraphNode>((node) => width * centers[node.group % centers.length]).strength(0.58))
        .force('y', forceY<GraphNode>(height / 2).strength(0.12));
      return;
    }

    simulation
      .force('center', null)
      .force('x', forceX<GraphNode>((node) => 44 + (node.born / Math.max(1, nodes.length - 1)) * (width - 88)).strength(0.66))
      .force('y', forceY<GraphNode>((node) => height * (0.28 + node.group * 0.145)).strength(0.58));
  }

  function applyCommunityForces() {
    if (!simulation) return;
    const centers = [
      [0.28, 0.31],
      [0.71, 0.3],
      [0.3, 0.72],
      [0.7, 0.71],
    ];

    simulation
      .force('center', forceCenter(width / 2, height / 2).strength(0.018))
      .force(
        'x',
        forceX<GraphNode>((node) => {
          const center = centers[node.group % centers.length];
          if (activeCommunity === node.group) return width / 2;
          return width * center[0];
        }).strength((node: GraphNode) => (activeCommunity === node.group ? 0.38 : activeCommunity === null ? 0.12 : 0.08)),
      )
      .force(
        'y',
        forceY<GraphNode>((node) => {
          const center = centers[node.group % centers.length];
          if (activeCommunity === node.group) return height / 2;
          return height * center[1];
        }).strength((node: GraphNode) => (activeCommunity === node.group ? 0.38 : activeCommunity === null ? 0.12 : 0.08)),
      );
  }

  function ticked() {
    if (activeScene === 'trails') {
      for (const node of nodes) {
        const previous = node.trail[node.trail.length - 1];
        if (!previous || Math.hypot(nodeX(node) - previous.x, nodeY(node) - previous.y) > 2.8) {
          node.trail.push({ x: nodeX(node), y: nodeY(node) });
          if (node.trail.length > 54) node.trail.shift();
        }
      }
    }

    if (activeScene !== 'collisions') {
      const padding = 28;
      for (const node of nodes) {
        if (node.fx == null) node.x = clamp(nodeX(node), padding, width - padding);
        if (node.fy == null) node.y = clamp(nodeY(node), padding, height - padding);
      }
    }
  }

  function reheat(alpha = 0.6, ticks = 140) {
    if (!simulation) return;
    if (reducedMotion) {
      simulation.stop().alpha(alpha);
      for (let index = 0; index < ticks; index += 1) simulation.tick();
      ticked();
      return;
    }
    if (!paused) simulation.alpha(alpha).restart();
  }

  function setScene(scene: SceneId) {
    if (scene === activeScene) return;
    activeScene = scene;
    paused = false;
    resetScene();
  }

  function setLayout(mode: LayoutMode) {
    layoutMode = mode;
    applyLayoutForces();
    reheat(0.85, 190);
  }

  function togglePause() {
    paused = !paused;
    if (paused) simulation?.stop();
    else if (!reducedMotion) simulation?.alpha(0.35).restart();
  }

  function explode() {
    const centerX = width / 2;
    const centerY = height / 2;
    for (const node of nodes) {
      const dx = nodeX(node) - centerX || Math.cos(node.born);
      const dy = nodeY(node) - centerY || Math.sin(node.born);
      const distance = Math.max(30, Math.hypot(dx, dy));
      const force = activeScene === 'collisions' ? 16 : 9;
      node.vx = (node.vx ?? 0) + (dx / distance) * force;
      node.vy = (node.vy ?? 0) + (dy / distance) * force;
      if (activeScene === 'trails') node.trail = [];
    }
    if (!paused && !reducedMotion) simulation?.alpha(0.55).restart();
  }

  function addBodies(count = 12) {
    const random = randomFactory(seed + nodes.length * 19);
    const graphPointer = pointer.inside ? screenToGraph(pointer.x, pointer.y) : { x: width / 2, y: height / 2 };
    const additions = Array.from({ length: count }, (_, offset): GraphNode => ({
      id: `b${nodes.length + offset}-${Date.now()}`,
      label: `Body ${nodes.length + offset + 1}`,
      group: (nodes.length + offset) % 4,
      radius: 6 + Math.pow(random(), 1.7) * 23,
      importance: random(),
      born: nodes.length + offset,
      trail: [],
      x: graphPointer.x + (random() - 0.5) * 36,
      y: graphPointer.y + (random() - 0.5) * 36,
      vx: (random() - 0.5) * 7,
      vy: (random() - 0.5) * 7,
    }));
    nodes = [...nodes, ...additions];
    simulation?.nodes(nodes);
    configureForces();
    reheat(0.75, 150);
  }

  function clearWells() {
    wells = [];
    status = 'Gravity wells cleared. Click the field to paint a new one.';
  }

  function releaseSelection() {
    selectedIds = new Set();
    status = currentScene().hint;
  }

  function triggerCascade(origin: GraphNode) {
    const adjacency = makeAdjacency();
    const distances = new Map<string, number>([[origin.id, 0]]);
    const edgeDistances = new Map<string, number>();
    const queue = [origin.id];

    while (queue.length) {
      const current = queue.shift()!;
      const distance = distances.get(current)!;
      for (const neighbor of adjacency.get(current) ?? []) {
        const key = current < neighbor ? `${current}|${neighbor}` : `${neighbor}|${current}`;
        edgeDistances.set(key, Math.min(edgeDistances.get(key) ?? Infinity, distance));
        if (!distances.has(neighbor)) {
          distances.set(neighbor, distance + 1);
          queue.push(neighbor);
        }
      }
    }

    pulseDistances = distances;
    pulseEdgeDistances = edgeDistances;
    pulseStart = performance.now();
    status = `Signal launched from ${origin.label}.`;
  }

  function choosePathNode(node: GraphNode) {
    if (!pathStart || pathEnd) {
      pathStart = node;
      pathEnd = null;
      pathIds = new Set([node.id]);
      pathEdgeIds = new Set();
      status = `Start: ${node.label}. Choose an end node.`;
      return;
    }

    pathEnd = node;
    const result = shortestPath(pathStart.id, node.id);
    pathIds = new Set(result.nodes);
    pathEdgeIds = new Set(result.edges);
    pulseStart = performance.now();
    status = result.nodes.length > 1 ? `Shortest path: ${result.nodes.length - 1} hops.` : 'No path found.';
  }

  function makeAdjacency() {
    const adjacency = new Map<string, string[]>();
    for (const node of nodes) adjacency.set(node.id, []);
    for (const link of links) {
      const source = sourceNode(link);
      const target = targetNode(link);
      adjacency.get(source.id)?.push(target.id);
      adjacency.get(target.id)?.push(source.id);
    }
    return adjacency;
  }

  function shortestPath(startId: string, endId: string) {
    const adjacency = makeAdjacency();
    const queue = [startId];
    const previous = new Map<string, string | null>([[startId, null]]);

    while (queue.length) {
      const current = queue.shift()!;
      if (current === endId) break;
      for (const neighbor of adjacency.get(current) ?? []) {
        if (previous.has(neighbor)) continue;
        previous.set(neighbor, current);
        queue.push(neighbor);
      }
    }

    if (!previous.has(endId)) return { nodes: [startId], edges: [] as string[] };
    const path: string[] = [];
    let current: string | null = endId;
    while (current) {
      path.push(current);
      current = previous.get(current) ?? null;
    }
    path.reverse();
    return {
      nodes: path,
      edges: path.slice(1).map((id, index) => (path[index] < id ? `${path[index]}|${id}` : `${id}|${path[index]}`)),
    };
  }

  function focusClosestCommunity(screenX: number, screenY: number) {
    const graph = screenToGraph(screenX, screenY);
    let closestGroup: number | null = null;
    let closestDistance = Infinity;
    for (let group = 0; group < 4; group += 1) {
      const groupNodes = nodes.filter((node) => node.group === group);
      if (!groupNodes.length) continue;
      const centerX = groupNodes.reduce((sum, node) => sum + nodeX(node), 0) / groupNodes.length;
      const centerY = groupNodes.reduce((sum, node) => sum + nodeY(node), 0) / groupNodes.length;
      const distance = Math.hypot(graph.x - centerX, graph.y - centerY);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestGroup = group;
      }
    }
    if (closestDistance >= Math.min(width, height) * 0.24 || closestGroup === null) return false;
    activeCommunity = activeCommunity === closestGroup ? null : closestGroup;
    applyCommunityForces();
    reheat(0.8, 180);
    status = activeCommunity === null ? 'All communities released.' : `Community ${activeCommunity + 1} pulled into focus.`;
    return true;
  }

  function readTheme() {
    const styles = getComputedStyle(document.documentElement);
    colors = {
      bg: styles.getPropertyValue('--bg').trim() || '#fff8e8',
      surface: styles.getPropertyValue('--surface-strong').trim() || '#fffdf5',
      text: styles.getPropertyValue('--text').trim() || '#173d3b',
      muted: styles.getPropertyValue('--muted').trim() || '#607874',
      line: styles.getPropertyValue('--line').trim() || 'rgba(24, 92, 87, .2)',
      accent: styles.getPropertyValue('--accent').trim() || '#0f7773',
      accentStrong: styles.getPropertyValue('--accent-strong').trim() || '#07524f',
      accentSoft: styles.getPropertyValue('--accent-soft').trim() || 'rgba(15, 119, 115, .13)',
      season: [1, 2, 3].map((index) => styles.getPropertyValue(`--season-${index}`).trim() || colors.accent),
    };
  }

  function resizeCanvas() {
    if (!shell || !canvas) return;
    const bounds = shell.getBoundingClientRect();
    const nextWidth = Math.max(320, Math.floor(bounds.width));
    const nextHeight = clamp(Math.round(nextWidth * 0.62), 430, 690);
    const oldWidth = width;
    const oldHeight = height;
    width = nextWidth;
    height = nextHeight;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.height = `${height}px`;

    if (oldWidth > 0 && oldHeight > 0 && nodes.length) {
      for (const node of nodes) {
        node.x = nodeX(node) * (width / oldWidth);
        node.y = nodeY(node) * (height / oldHeight);
        if (node.fx != null) node.fx *= width / oldWidth;
        if (node.fy != null) node.fy *= height / oldHeight;
        node.trail = [];
      }
      wells = wells.map((well) => ({ ...well, x: well.x * (width / oldWidth), y: well.y * (height / oldHeight) }));
    }

    configureForces();
    if (!paused && !reducedMotion) simulation?.alpha(0.4).restart();
  }

  function graphToScreen(x: number, y: number) {
    return { x: x * zoom.k + zoom.x, y: y * zoom.k + zoom.y };
  }

  function screenToGraph(x: number, y: number) {
    return { x: (x - zoom.x) / zoom.k, y: (y - zoom.y) / zoom.k };
  }

  function canvasPoint(event: PointerEvent | WheelEvent) {
    const bounds = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * width,
      y: ((event.clientY - bounds.top) / bounds.height) * height,
    };
  }

  function nodeAt(screenX: number, screenY: number) {
    const point = screenToGraph(screenX, screenY);
    for (let index = nodes.length - 1; index >= 0; index -= 1) {
      const node = nodes[index];
      if (Math.hypot(point.x - nodeX(node), point.y - nodeY(node)) <= node.radius + 7 / zoom.k) return node;
    }
    return null;
  }

  function wellAt(screenX: number, screenY: number) {
    const point = screenToGraph(screenX, screenY);
    return wells.find((well) => Math.hypot(point.x - well.x, point.y - well.y) < 18 / zoom.k) ?? null;
  }

  function handlePointerDown(event: PointerEvent) {
    if (event.button !== 0) return;
    canvas.setPointerCapture(event.pointerId);
    const point = canvasPoint(event);
    pointer = { ...point, inside: true };
    const hitNode = nodeAt(point.x, point.y);

    if (event.shiftKey && activeScene !== 'gravity') {
      dragState = { kind: 'lasso', pointerId: event.pointerId, startX: point.x, startY: point.y, endX: point.x, endY: point.y };
      return;
    }

    if (activeScene === 'gravity') {
      const hitWell = wellAt(point.x, point.y);
      if (hitWell) {
        dragState = { kind: 'well', pointerId: event.pointerId, well: hitWell, moved: false, startX: point.x, startY: point.y };
        return;
      }
    }

    if (hitNode) {
      hitNode.fx = nodeX(hitNode);
      hitNode.fy = nodeY(hitNode);
      dragState = { kind: 'node', pointerId: event.pointerId, node: hitNode, moved: false, startX: point.x, startY: point.y };
      if (!paused && !reducedMotion) simulation?.alphaTarget(0.18).restart();
      return;
    }

    dragState = {
      kind: 'pan',
      pointerId: event.pointerId,
      startX: point.x,
      startY: point.y,
      originX: zoom.x,
      originY: zoom.y,
      moved: false,
    };
  }

  function handlePointerMove(event: PointerEvent) {
    const point = canvasPoint(event);
    pointer = { ...point, inside: true };

    if (!dragState) {
      hoverNode = nodeAt(point.x, point.y);
      canvas.style.cursor = hoverNode ? 'grab' : activeScene === 'gravity' ? 'crosshair' : 'default';
      if (activeScene === 'collisions' && !paused && !reducedMotion) simulation?.alpha(0.18).restart();
      return;
    }

    if (dragState.pointerId !== event.pointerId) return;

    if (dragState.kind === 'lasso') {
      dragState.endX = point.x;
      dragState.endY = point.y;
      return;
    }

    const moved = Math.hypot(point.x - dragState.startX, point.y - dragState.startY) > 4;
    dragState.moved ||= moved;

    if (dragState.kind === 'pan') {
      zoom = {
        ...zoom,
        x: dragState.originX + (point.x - dragState.startX),
        y: dragState.originY + (point.y - dragState.startY),
      };
      canvas.style.cursor = 'grabbing';
      return;
    }

    const graphPoint = screenToGraph(point.x, point.y);
    if (dragState.kind === 'well') {
      dragState.well.x = clamp(graphPoint.x, 20, width - 20);
      dragState.well.y = clamp(graphPoint.y, 20, height - 20);
      return;
    }

    const deltaX = graphPoint.x - (dragState.node.fx ?? nodeX(dragState.node));
    const deltaY = graphPoint.y - (dragState.node.fy ?? nodeY(dragState.node));
    const draggedIds = selectedIds.has(dragState.node.id) ? selectedIds : new Set([dragState.node.id]);
    for (const node of nodes) {
      if (!draggedIds.has(node.id)) continue;
      node.fx = nodeX(node) + deltaX;
      node.fy = nodeY(node) + deltaY;
    }
  }

  function handlePointerUp(event: PointerEvent) {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    const point = canvasPoint(event);

    if (dragState.kind === 'lasso') {
      const x1 = Math.min(dragState.startX, dragState.endX);
      const x2 = Math.max(dragState.startX, dragState.endX);
      const y1 = Math.min(dragState.startY, dragState.endY);
      const y2 = Math.max(dragState.startY, dragState.endY);
      const next = new Set<string>();
      for (const node of nodes) {
        const screen = graphToScreen(nodeX(node), nodeY(node));
        if (screen.x >= x1 && screen.x <= x2 && screen.y >= y1 && screen.y <= y2) next.add(node.id);
      }
      selectedIds = next;
      status = next.size ? `${next.size} nodes selected. Drag any selected node to move the group.` : 'No nodes selected.';
    } else if (dragState.kind === 'node') {
      const clickedNode = dragState.node;
      const draggedIds = selectedIds.has(clickedNode.id) ? selectedIds : new Set([clickedNode.id]);
      for (const node of nodes) {
        if (!draggedIds.has(node.id)) continue;
        node.fx = null;
        node.fy = null;
      }
      if (!dragState.moved) handleNodeClick(clickedNode);
      simulation?.alphaTarget(0);
    } else if (dragState.kind === 'well') {
      status = `${wells.length} gravity wells active.`;
    } else if (!dragState.moved) {
      handleBackgroundClick(point.x, point.y);
    }

    dragState = null;
    canvas.releasePointerCapture(event.pointerId);
    canvas.style.cursor = hoverNode ? 'grab' : 'default';
  }

  function handleNodeClick(node: GraphNode) {
    if (activeScene === 'cascade') {
      triggerCascade(node);
      return;
    }
    if (activeScene === 'pathfinder') {
      choosePathNode(node);
      return;
    }
    focusedNode = focusedNode?.id === node.id ? null : node;
    status = focusedNode ? `${node.label} focused. Connected nodes remain emphasized.` : currentScene().hint;
  }

  function handleBackgroundClick(screenX: number, screenY: number) {
    if (activeScene === 'gravity') {
      const point = screenToGraph(screenX, screenY);
      wells = [...wells, { id: ++wellSequence, x: point.x, y: point.y, strength: 0.07, phase: wellSequence * 1.7 }];
      status = `${wells.length} gravity wells active.`;
      reheat(0.45, 110);
      return;
    }

    if (activeScene === 'collisions') {
      addBodies(7);
      return;
    }

    if (activeScene === 'hulls' && focusClosestCommunity(screenX, screenY)) return;

    focusedNode = null;
    if (activeScene === 'pathfinder') {
      pathStart = null;
      pathEnd = null;
      pathIds = new Set();
      pathEdgeIds = new Set();
    }
  }

  function handleWheel(event: WheelEvent) {
    event.preventDefault();
    const point = canvasPoint(event);
    const graphPoint = screenToGraph(point.x, point.y);
    const factor = Math.exp(-event.deltaY * 0.0012);
    const nextK = clamp(zoom.k * factor, 0.55, 3.4);
    zoom = {
      x: point.x - graphPoint.x * nextK,
      y: point.y - graphPoint.y * nextK,
      k: nextK,
    };
  }

  function handlePointerLeave() {
    pointer.inside = false;
    hoverNode = null;
  }

  function neighborhood(node: GraphNode | null) {
    if (!node) return new Set<string>();
    const result = new Set([node.id]);
    for (const link of links) {
      const source = sourceNode(link);
      const target = targetNode(link);
      if (source.id === node.id) result.add(target.id);
      if (target.id === node.id) result.add(source.id);
    }
    return result;
  }

  function convexHull(points: Array<[number, number]>) {
    if (points.length < 3) return points;
    const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cross = (origin: [number, number], a: [number, number], b: [number, number]) =>
      (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0]);
    const lower: Array<[number, number]> = [];
    for (const point of sorted) {
      while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) lower.pop();
      lower.push(point);
    }
    const upper: Array<[number, number]> = [];
    for (let index = sorted.length - 1; index >= 0; index -= 1) {
      const point = sorted[index];
      while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) upper.pop();
      upper.push(point);
    }
    lower.pop();
    upper.pop();
    return [...lower, ...upper];
  }

  function roundedHull(points: Array<[number, number]>, padding = 24) {
    if (points.length < 3) return points;
    const center = points.reduce((sum, point) => [sum[0] + point[0], sum[1] + point[1]], [0, 0]);
    center[0] /= points.length;
    center[1] /= points.length;
    return points.map(([x, y]) => {
      const dx = x - center[0];
      const dy = y - center[1];
      const distance = Math.max(1, Math.hypot(dx, dy));
      return [x + (dx / distance) * padding, y + (dy / distance) * padding] as [number, number];
    });
  }

  function drawFrame(time: number) {
    animationFrame = requestAnimationFrame(drawFrame);
    if (!context) return;
    if (reducedMotion && time - lastFrame < 80) return;
    lastFrame = time;

    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);
    drawBackground(time);

    context.save();
    context.translate(zoom.x, zoom.y);
    context.scale(zoom.k, zoom.k);

    if (activeScene === 'trails') drawTrails();
    if (activeScene === 'hulls') drawHulls();
    if (activeScene !== 'gravity' && activeScene !== 'collisions' && activeScene !== 'trails') drawLinks(time);
    if (activeScene === 'gravity') drawWells(time);
    drawNodes(time);
    context.restore();

    drawLasso();
    drawPointerField();
  }

  function drawBackground(time: number) {
    if (!context) return;
    context.fillStyle = colors.surface;
    context.fillRect(0, 0, width, height);

    const gridSize = 34;
    context.save();
    context.globalAlpha = 0.33;
    context.strokeStyle = colors.line;
    context.lineWidth = 1;
    const offsetX = ((zoom.x % (gridSize * zoom.k)) + gridSize * zoom.k) % (gridSize * zoom.k);
    const offsetY = ((zoom.y % (gridSize * zoom.k)) + gridSize * zoom.k) % (gridSize * zoom.k);
    for (let x = offsetX; x < width; x += gridSize * zoom.k) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
    for (let y = offsetY; y < height; y += gridSize * zoom.k) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
    context.restore();

    if (activeScene === 'gravity') {
      const glow = context.createRadialGradient(width / 2, height / 2, 20, width / 2, height / 2, Math.max(width, height) * 0.65);
      glow.addColorStop(0, colors.accentSoft);
      glow.addColorStop(1, 'transparent');
      context.fillStyle = glow;
      context.fillRect(0, 0, width, height);
    }

    if (activeScene === 'trails') {
      context.save();
      context.globalAlpha = 0.08 + Math.sin(time * 0.0004) * 0.02;
      context.fillStyle = colors.accent;
      context.beginPath();
      context.arc(width / 2, height / 2, Math.min(width, height) * 0.34, 0, Math.PI * 2);
      context.fill();
      context.restore();
    }
  }

  function drawLinks(time: number) {
    if (!context) return;
    const focusSet = neighborhood(hoverNode ?? focusedNode);
    const cascadeElapsed = time - pulseStart;

    for (const link of links) {
      const source = sourceNode(link);
      const target = targetNode(link);
      const key = linkKey(source, target);
      let alpha = 0.34;
      let widthValue = 1.15;
      let stroke = colors.line;

      if (focusSet.size) {
        const active = focusSet.has(source.id) && focusSet.has(target.id) && (source.id === (hoverNode ?? focusedNode)?.id || target.id === (hoverNode ?? focusedNode)?.id);
        alpha = active ? 0.9 : 0.08;
        widthValue = active ? 2.1 : 0.8;
        if (active) stroke = colors.accent;
      }

      if (activeScene === 'cascade' && pulseEdgeDistances.size) {
        const distance = pulseEdgeDistances.get(key);
        const phase = distance === undefined ? -10 : (cascadeElapsed - distance * 260) / 420;
        const pulse = phase >= 0 && phase <= 1 ? Math.sin(phase * Math.PI) : 0;
        alpha = distance === undefined ? 0.08 : 0.18 + pulse * 0.82;
        widthValue = 1 + pulse * 4;
        stroke = pulse > 0 ? colors.accent : colors.line;
      }

      if (activeScene === 'pathfinder' && pathStart) {
        const active = pathEdgeIds.has(key);
        alpha = active ? 0.95 : 0.06;
        widthValue = active ? 3.5 : 0.8;
        stroke = active ? colors.accent : colors.line;
      }

      context.save();
      context.globalAlpha = alpha;
      context.strokeStyle = stroke;
      context.lineWidth = widthValue / zoom.k;
      context.beginPath();
      context.moveTo(nodeX(source), nodeY(source));
      const dx = nodeX(target) - nodeX(source);
      const dy = nodeY(target) - nodeY(source);
      const bend = ((source.born + target.born) % 2 ? 1 : -1) * Math.min(18, Math.hypot(dx, dy) * 0.08);
      const middleX = (nodeX(source) + nodeX(target)) / 2 - (dy / Math.max(1, Math.hypot(dx, dy))) * bend;
      const middleY = (nodeY(source) + nodeY(target)) / 2 + (dx / Math.max(1, Math.hypot(dx, dy))) * bend;
      context.quadraticCurveTo(middleX, middleY, nodeX(target), nodeY(target));
      context.stroke();
      context.restore();

      if (activeScene === 'living' || (activeScene === 'pathfinder' && pathEdgeIds.has(key))) {
        const speed = activeScene === 'pathfinder' ? 0.00055 : 0.00018 + link.weight * 0.00006;
        const phase = (time * speed + source.born * 0.071 + target.born * 0.037) % 1;
        const oneMinus = 1 - phase;
        const particleX = oneMinus * oneMinus * nodeX(source) + 2 * oneMinus * phase * middleX + phase * phase * nodeX(target);
        const particleY = oneMinus * oneMinus * nodeY(source) + 2 * oneMinus * phase * middleY + phase * phase * nodeY(target);
        context.save();
        context.globalAlpha = activeScene === 'pathfinder' ? 1 : focusSet.size ? 0.9 : 0.72;
        context.fillStyle = colors.accent;
        context.beginPath();
        context.arc(particleX, particleY, (activeScene === 'pathfinder' ? 3.8 : 2.5) / zoom.k, 0, Math.PI * 2);
        context.fill();
        context.restore();
      }
    }
  }

  function drawHulls() {
    if (!context) return;
    const groups = new Map<number, GraphNode[]>();
    for (const node of nodes) {
      if (!groups.has(node.group)) groups.set(node.group, []);
      groups.get(node.group)?.push(node);
    }

    for (const [group, groupNodes] of groups) {
      const hull = roundedHull(
        convexHull(groupNodes.map((node) => [nodeX(node), nodeY(node)] as [number, number])),
        activeCommunity === group ? 38 : 26,
      );
      if (hull.length < 3) continue;
      context.save();
      context.globalAlpha = activeCommunity === null || activeCommunity === group ? 0.13 : 0.045;
      context.fillStyle = colors.season[group % colors.season.length];
      context.strokeStyle = colors.season[group % colors.season.length];
      context.lineWidth = (activeCommunity === group ? 2.4 : 1.2) / zoom.k;
      context.beginPath();
      context.moveTo(hull[0][0], hull[0][1]);
      for (let index = 1; index < hull.length; index += 1) context.lineTo(hull[index][0], hull[index][1]);
      context.closePath();
      context.fill();
      context.globalAlpha *= 3.3;
      context.stroke();
      context.restore();
    }
  }

  function drawWells(time: number) {
    if (!context) return;
    for (const well of wells) {
      const pulse = 1 + Math.sin(time * 0.002 + well.phase) * 0.12;
      const gradient = context.createRadialGradient(well.x, well.y, 0, well.x, well.y, 54 * pulse);
      gradient.addColorStop(0, colors.accent);
      gradient.addColorStop(0.18, colors.accentSoft);
      gradient.addColorStop(1, 'transparent');
      context.fillStyle = gradient;
      context.beginPath();
      context.arc(well.x, well.y, 54 * pulse, 0, Math.PI * 2);
      context.fill();
      context.strokeStyle = colors.accent;
      context.globalAlpha = 0.78;
      context.lineWidth = 1.4 / zoom.k;
      context.beginPath();
      context.arc(well.x, well.y, 10 * pulse, 0, Math.PI * 2);
      context.stroke();
      context.globalAlpha = 1;
    }
  }

  function drawTrails() {
    if (!context) return;
    for (const node of nodes) {
      if (node.trail.length < 2) continue;
      context.save();
      context.strokeStyle = colors.season[node.group % colors.season.length];
      context.lineWidth = Math.max(0.8, node.radius * 0.32) / zoom.k;
      context.lineCap = 'round';
      context.lineJoin = 'round';
      for (let index = 1; index < node.trail.length; index += 1) {
        context.globalAlpha = (index / node.trail.length) * 0.48;
        context.beginPath();
        context.moveTo(node.trail[index - 1].x, node.trail[index - 1].y);
        context.lineTo(node.trail[index].x, node.trail[index].y);
        context.stroke();
      }
      context.restore();
    }
  }

  function drawNodes(time: number) {
    if (!context) return;
    const focus = hoverNode ?? focusedNode;
    const focusSet = neighborhood(focus);
    const cascadeElapsed = time - pulseStart;

    for (const node of nodes) {
      const x = nodeX(node);
      const y = nodeY(node);
      let alpha = 1;
      let radius = node.radius;
      let fill = colors.season[node.group % colors.season.length];
      let ring = false;

      if (focusSet.size && !focusSet.has(node.id)) alpha = 0.17;
      if (selectedIds.has(node.id)) {
        ring = true;
        radius += 2;
      }

      if (activeScene === 'cascade' && pulseDistances.size) {
        const distance = pulseDistances.get(node.id);
        const phase = distance === undefined ? -10 : (cascadeElapsed - distance * 260) / 520;
        const pulse = phase >= 0 && phase <= 1 ? Math.sin(phase * Math.PI) : 0;
        alpha = distance === undefined ? 0.14 : 0.48 + pulse * 0.52;
        radius += pulse * 9;
        if (pulse > 0) fill = colors.accent;
      }

      if (activeScene === 'pathfinder' && pathStart) {
        const active = pathIds.has(node.id);
        alpha = active ? 1 : 0.12;
        if (active) {
          const pulse = pathEnd ? 0.5 + Math.sin(time * 0.005 - node.born) * 0.5 : 0;
          radius += pulse * 3;
          fill = node.id === pathStart.id || node.id === pathEnd?.id ? colors.accentStrong : colors.accent;
        }
      }

      if (activeScene === 'collisions') {
        alpha = 0.72 + node.importance * 0.28;
      }

      if (activeScene === 'gravity' || activeScene === 'trails') {
        alpha = 0.52 + node.importance * 0.48;
      }

      context.save();
      context.globalAlpha = alpha;
      context.fillStyle = fill;
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.fill();

      if (node === hoverNode || node === focusedNode || ring || node === pathStart || node === pathEnd) {
        context.globalAlpha = 0.95;
        context.strokeStyle = node === hoverNode || node === focusedNode ? colors.accentStrong : colors.text;
        context.lineWidth = 2.2 / zoom.k;
        context.beginPath();
        context.arc(x, y, radius + 5 / zoom.k, 0, Math.PI * 2);
        context.stroke();
      }

      if (activeScene !== 'gravity' && activeScene !== 'trails' && activeScene !== 'collisions') {
        context.globalAlpha = alpha * 0.65;
        context.fillStyle = colors.surface;
        context.beginPath();
        context.arc(x - radius * 0.2, y - radius * 0.22, Math.max(1.6, radius * 0.2), 0, Math.PI * 2);
        context.fill();
      }
      context.restore();

      const shouldLabel =
        labelsVisible &&
        activeScene !== 'gravity' &&
        activeScene !== 'trails' &&
        activeScene !== 'collisions' &&
        (zoom.k > 1.18 || node.importance > 0.85 || node === hoverNode || node === focusedNode || pathIds.has(node.id));

      if (shouldLabel) {
        context.save();
        context.globalAlpha = alpha;
        context.font = `${clamp(11 / zoom.k, 7, 12)}px ui-monospace, SFMono-Regular, Menlo, monospace`;
        context.textAlign = 'center';
        context.textBaseline = 'top';
        context.fillStyle = colors.text;
        context.fillText(node.label, x, y + radius + 8 / zoom.k);
        context.restore();
      }
    }
  }

  function drawLasso() {
    if (!context || dragState?.kind !== 'lasso') return;
    const x = Math.min(dragState.startX, dragState.endX);
    const y = Math.min(dragState.startY, dragState.endY);
    const w = Math.abs(dragState.endX - dragState.startX);
    const h = Math.abs(dragState.endY - dragState.startY);
    context.save();
    context.fillStyle = colors.accentSoft;
    context.strokeStyle = colors.accent;
    context.setLineDash([7, 5]);
    context.lineWidth = 1.5;
    context.fillRect(x, y, w, h);
    context.strokeRect(x, y, w, h);
    context.restore();
  }

  function drawPointerField() {
    if (!context || activeScene !== 'collisions' || !pointer.inside) return;
    context.save();
    context.strokeStyle = colors.accent;
    context.globalAlpha = 0.5;
    context.lineWidth = 1.5;
    context.setLineDash(pointerMode === 'repel' ? [4, 5] : []);
    context.beginPath();
    context.arc(pointer.x, pointer.y, 64, 0, Math.PI * 2);
    context.stroke();
    context.restore();
  }

  function handleKeyDown(event: KeyboardEvent) {
    const panStep = event.shiftKey ? 70 : 32;
    if (event.key === ' ' || event.key.toLowerCase() === 'p') {
      event.preventDefault();
      togglePause();
      return;
    }
    if (event.key.toLowerCase() === 'r') {
      resetScene(true);
      return;
    }
    if (event.key.toLowerCase() === 'e') {
      explode();
      return;
    }
    if (event.key === '+' || event.key === '=') {
      event.preventDefault();
      const nextK = clamp(zoom.k * 1.18, 0.55, 3.4);
      zoom = { x: width / 2 - ((width / 2 - zoom.x) / zoom.k) * nextK, y: height / 2 - ((height / 2 - zoom.y) / zoom.k) * nextK, k: nextK };
      return;
    }
    if (event.key === '-' || event.key === '_') {
      event.preventDefault();
      const nextK = clamp(zoom.k / 1.18, 0.55, 3.4);
      zoom = { x: width / 2 - ((width / 2 - zoom.x) / zoom.k) * nextK, y: height / 2 - ((height / 2 - zoom.y) / zoom.k) * nextK, k: nextK };
      return;
    }
    const directions: Record<string, [number, number]> = { ArrowLeft: [panStep, 0], ArrowRight: [-panStep, 0], ArrowUp: [0, panStep], ArrowDown: [0, -panStep] };
    const direction = directions[event.key];
    if (direction) {
      event.preventDefault();
      zoom = { ...zoom, x: zoom.x + direction[0], y: zoom.y + direction[1] };
    }
  }


  onMount(() => {
    context = canvas.getContext('2d');
    reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion = reducedMotionQuery.matches;
    const motionListener = (event: MediaQueryListEvent) => {
      reducedMotion = event.matches;
      resetScene();
    };
    reducedMotionQuery.addEventListener('change', motionListener);

    readTheme();
    themeObserver = new MutationObserver(readTheme);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-season'] });

    resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(shell);
    resizeCanvas();
    resetScene();
    animationFrame = requestAnimationFrame(drawFrame);

    return () => {
      reducedMotionQuery?.removeEventListener('change', motionListener);
      window.cancelAnimationFrame(animationFrame);
      simulation?.stop();
      resizeObserver?.disconnect();
      themeObserver?.disconnect();
    };
  });
</script>

<div class="d3-lab">
  <div class="d3-lab__intro">
    <div>
      <p class="d3-lab__eyebrow">Interactive simulation gallery</p>
      <h2>{currentScene().label}</h2>
      <p>{currentScene().description}</p>
    </div>
    <div class="d3-lab__stats" role="group" aria-label="Simulation status">
      <span><strong>{nodes.length}</strong> nodes</span>
      <span><strong>{links.length}</strong> links</span>
      <span><strong>{zoom.k.toFixed(1)}×</strong> zoom</span>
    </div>
  </div>

  <div class="d3-lab__scene-tabs" role="group" aria-label="D3 simulation demos">
    {#each scenes as scene, index}
      <button
        type="button"
        class:active={scene.id === activeScene}
        aria-pressed={scene.id === activeScene}
        on:click={() => setScene(scene.id)}
      >
        <span>{String(index + 1).padStart(2, '0')}</span>
        {scene.label}
      </button>
    {/each}
  </div>

  <div class="d3-lab__toolbar" role="group" aria-label="Simulation controls">
    <div class="d3-lab__toolbar-group">
      <button type="button" on:click={togglePause}>{paused ? 'Play' : 'Pause'}</button>
      <button type="button" on:click={explode}>Explode</button>
      <button type="button" on:click={() => resetScene(true)}>Regenerate</button>
      <button type="button" class:active={labelsVisible} aria-pressed={labelsVisible} on:click={() => (labelsVisible = !labelsVisible)}>
        Labels
      </button>
    </div>

    {#if activeScene === 'morph'}
      <div class="d3-lab__toolbar-group d3-lab__toolbar-group--scroll" role="group" aria-label="Layout choices">
        {#each ['organic', 'orbit', 'grid', 'split', 'timeline'] as mode}
          <button type="button" class:active={layoutMode === mode} aria-pressed={layoutMode === mode} on:click={() => setLayout(mode as LayoutMode)}>
            {mode}
          </button>
        {/each}
      </div>
    {:else if activeScene === 'gravity'}
      <div class="d3-lab__toolbar-group">
        <button type="button" on:click={clearWells}>Clear wells</button>
        <span>{wells.length} active</span>
      </div>
    {:else if activeScene === 'collisions'}
      <div class="d3-lab__toolbar-group">
        <button type="button" class:active={pointerMode === 'attract'} aria-pressed={pointerMode === 'attract'} on:click={() => (pointerMode = 'attract')}>
          Attract
        </button>
        <button type="button" class:active={pointerMode === 'repel'} aria-pressed={pointerMode === 'repel'} on:click={() => (pointerMode = 'repel')}>
          Repel
        </button>
        <button type="button" on:click={() => addBodies(12)}>Add bodies</button>
      </div>
    {:else if selectedIds.size}
      <div class="d3-lab__toolbar-group">
        <span>{selectedIds.size} selected</span>
        <button type="button" on:click={releaseSelection}>Release</button>
      </div>
    {/if}
  </div>

  <div class="d3-lab__canvas-shell" bind:this={shell}>
    <canvas
      bind:this={canvas}
      aria-label={`${currentScene().label}: ${currentScene().description}`}
      role="application"
      tabindex="0"
      on:pointerdown={handlePointerDown}
      on:pointermove={handlePointerMove}
      on:pointerup={handlePointerUp}
      on:pointercancel={handlePointerUp}
      on:pointerleave={handlePointerLeave}
      on:wheel|nonpassive={handleWheel}
      on:keydown={handleKeyDown}
    ></canvas>
    <div class="d3-lab__canvas-badge" aria-hidden="true">D3 force engine · Canvas renderer</div>
  </div>

  <div class="d3-lab__footer">
    <p aria-live="polite">{status}</p>
    <p>Drag to pan · Wheel or +/− to zoom · Shift-drag to lasso · P pause · R regenerate</p>
  </div>

  <section class="d3-lab__feature-grid" aria-label="Features demonstrated on this page">
    <article>
      <span>Physics</span>
      <h3>Composable forces</h3>
      <p>Links, charge, collision, centering, radial targets, custom gravity, boundaries, and pointer fields.</p>
    </article>
    <article>
      <span>Interaction</span>
      <h3>Direct manipulation</h3>
      <p>Node dragging, group dragging, panning, zooming, lasso selection, hover focus, and click-driven state.</p>
    </article>
    <article>
      <span>Animation</span>
      <h3>Data that moves</h3>
      <p>Layout morphs, traveling edge particles, BFS cascades, path animation, shockwaves, and persistent trails.</p>
    </article>
    <article>
      <span>Geometry</span>
      <h3>Derived structure</h3>
      <p>Convex community hulls, curved edges, neighborhood emphasis, shortest paths, and semantic zoom labels.</p>
    </article>
  </section>
</div>
