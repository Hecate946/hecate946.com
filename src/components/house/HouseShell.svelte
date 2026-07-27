<script lang="ts">
  const upperWindows = [
    { x: 297, y: 307, width: 86, height: 132 },
    { x: 515, y: 307, width: 85, height: 132 },
    { x: 805, y: 307, width: 86, height: 147 },
    { x: 1098, y: 307, width: 86, height: 132 },
    { x: 1315, y: 307, width: 86, height: 132 },
  ] as const;

  const lowerWindows = [
    { x: 295, y: 562, width: 299, height: 181 },
    { x: 1100, y: 562, width: 305, height: 181 },
  ] as const;

  const upperColumns = [1 / 3, 2 / 3] as const;
  const upperRows = [1 / 4, 2 / 4, 3 / 4] as const;
  const lowerColumns = [1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7] as const;
  const lowerRows = [1 / 5, 2 / 5, 3 / 5, 4 / 5] as const;
</script>

<g class="house-shell" aria-hidden="true">
  <!-- The SVG uses the frozen PNG's native 1672 × 941 coordinate system. -->

  <!-- Main roof masses. -->
  <path class="house-shell__ink" d="M177 231 482 177H720L650 231Z" />
  <path class="house-shell__ink" d="M964 177H1200L1505 231H1055Z" />
  <path class="house-shell__ink house-shell__outlined" d="M633 230 850 92 1042 230Z" />

  <!-- Pediment inset lines and circular oculus. -->
  <path class="house-shell__line" d="M653 229 850 104 1024 229" />
  <path class="house-shell__line" d="M674 229 850 117 1004 229" />
  <circle class="house-shell__line" cx="850" cy="182" r="32" />
  <circle class="house-shell__line" cx="850" cy="182" r="21" />

  <!-- Full-width eave and cornice. -->
  <path class="house-shell__ink house-shell__outlined" d="M141 238H1558L1512 271H186Z" />
  <path class="house-shell__line" d="M147 243H1552" />
  <path class="house-shell__line" d="M179 271H1513" />
  <path class="house-shell__line" d="M187 280H1511" />

  <!-- Upper and lower wall fields. -->
  <rect class="house-shell__ink" x="192" y="281" width="1314" height="215" />
  <rect class="house-shell__ink" x="192" y="515" width="1314" height="293" />
  <rect class="house-shell__ink" x="689" y="279" width="318" height="500" />

  <!-- Central portico cornice, copied from the frozen silhouette. -->
  <path class="house-shell__ink house-shell__outlined" d="M632 227H1049V241H632Z" />
  <path class="house-shell__ink house-shell__outlined" d="M644 240H1054V254H644Z" />
  <path class="house-shell__ink house-shell__outlined" d="M653 250H1044V265H653Z" />
  <path class="house-shell__ink house-shell__outlined" d="M661 259H1038V272H661Z" />
  <path class="house-shell__ink house-shell__outlined" d="M674 269H1023V282H674Z" />

  <!-- Paired portico boundary lines create the narrow dark reveals in the PNG. -->
  <path class="house-shell__line" d="M684 280V491M689 280V491" />
  <path class="house-shell__line" d="M1007 280V491M1012 280V491" />
  <path class="house-shell__line" d="M684 511V778M689 511V778" />
  <path class="house-shell__line" d="M1007 511V778M1012 511V778" />

  <!-- Floor division and the center projection. -->
  <path class="house-shell__ink house-shell__outlined" d="M186 496H1512V515H186Z" />
  <path class="house-shell__ink house-shell__outlined" d="M658 488H1037V511H658Z" />

  <!-- Five vertically aligned upper windows, each with a 3 × 4 pane grid. -->
  {#each upperWindows as window}
    <g class="house-shell__window">
      <rect
        class="house-shell__window-body"
        x={window.x}
        y={window.y}
        width={window.width}
        height={window.height}
      />
      {#each upperColumns as ratio}
        <path
          class="house-shell__window-grid"
          d={`M${window.x + window.width * ratio} ${window.y}V${window.y + window.height}`}
        />
      {/each}
      {#each upperRows as ratio}
        <path
          class="house-shell__window-grid"
          d={`M${window.x} ${window.y + window.height * ratio}H${window.x + window.width}`}
        />
      {/each}
      <rect
        class="house-shell__window-sill"
        x={window.x - 12}
        y={window.y + window.height}
        width={window.width + 24}
        height="10"
      />
    </g>
  {/each}

  <!-- Two broad first-story windows. The frozen PNG resolved to a 7 × 5 grid. -->
  {#each lowerWindows as window}
    <g class="house-shell__window house-shell__window--large">
      <rect
        class="house-shell__window-lintel"
        x={window.x - 12}
        y={window.y - 16}
        width={window.width + 24}
        height="16"
      />
      <rect
        class="house-shell__window-body"
        x={window.x}
        y={window.y}
        width={window.width}
        height={window.height}
      />
      {#each lowerColumns as ratio}
        <path
          class="house-shell__window-grid"
          d={`M${window.x + window.width * ratio} ${window.y}V${window.y + window.height}`}
        />
      {/each}
      {#each lowerRows as ratio}
        <path
          class="house-shell__window-grid"
          d={`M${window.x} ${window.y + window.height * ratio}H${window.x + window.width}`}
        />
      {/each}
      <rect
        class="house-shell__window-sill"
        x={window.x - 12}
        y={window.y + window.height}
        width={window.width + 24}
        height="16"
      />
    </g>
  {/each}

  <!-- Double-line pointed arch entrance. -->
  <path
    class="house-shell__line house-shell__door-line"
    d="M770 778V648Q770 589 850 562Q929 589 929 648V778"
  />
  <path
    class="house-shell__line house-shell__door-line"
    d="M783 778V651Q783 602 850 576Q916 602 916 651V778"
  />
  <path class="house-shell__line house-shell__door-center" d="M850 576V778" />

  <!-- Three centered entry steps. -->
  <path class="house-shell__ink house-shell__outlined" d="M482 770H1220V784H482Z" />
  <path class="house-shell__ink house-shell__outlined" d="M448 797H1254V815H448Z" />
  <path class="house-shell__ink house-shell__outlined" d="M433 819H1269V833H433Z" />
</g>
