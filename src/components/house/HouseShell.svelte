<g class="house-shell" aria-hidden="true">
  <!-- Ground shadow -->
  <ellipse class="house-shell__ground-shadow" cx="706" cy="779" rx="560" ry="22" />

  <!-- Main front walls -->
  <rect class="house-shell__front-wall" x="140" y="290" width="1120" height="430" rx="2" />
  <rect class="house-shell__front-wall" x="170" y="286" width="255" height="434" rx="2" />

  <!-- Roof: fully front-facing and symmetrical -->
  <path class="house-shell__roof" d="M108 292 275 108H1138L1305 292Z" />
  <path class="house-shell__roof-lip" d="M123 286H1290L1270 308H143Z" />
  <path class="house-shell__roof-highlight" d="M285 113H1130" />
  <path class="house-shell__ridge" d="M275 108H1138" />

  <!-- Entry gable -->
  <path class="house-shell__entry-face" d="M180 320 352 152 524 320V720H180Z" />
  <path class="house-shell__entry-roof-left" d="M163 323 351 136 371 156 183 342Z" />
  <path class="house-shell__entry-roof-right" d="M351 136 541 325 521 343 331 156Z" />
  <path class="house-shell__entry-timber" d="M351 154V320M204 320 351 154 500 320" />

  <!-- Taller brick chimney -->
  <g class="house-shell__chimney">
    <rect x="1108" y="95" width="72" height="165" />
    <path d="M1092 86H1196V108H1092Z" />
    <path d="M1119 120H1169M1119 145H1169M1119 170H1169M1119 195H1169M1119 220H1169M1119 245H1169" />
    <path d="M1144 108V260M1129 132V158M1159 132V158M1129 182V208M1159 182V208M1129 232V258M1159 232V258" />
  </g>

  <!-- Trim bands to help house proportions read cleanly -->
  <path class="house-shell__timber" d="M140 308H1260M140 718H1260M170 286V720M1240 286V720" />
  <path class="house-shell__upper-trim" d="M495 307H1230V319H495Z" />

  <!-- Foundation -->
  <rect class="house-shell__foundation" x="128" y="708" width="1144" height="62" />
  <path class="house-shell__foundation-cap" d="M116 699H1284V716H116Z" />
  <path class="house-shell__foundation-highlight" d="M150 728H1246" />

  <!-- Arched double door aligned under the circular window -->
  <path class="house-shell__door-frame" d="M214 714V505A87 87 0 0 1 388 505V714Z" />
  <path class="house-shell__door" d="M234 714V526A67 67 0 0 1 368 526V714Z" />
  <path class="house-shell__door-panels" d="M301 526V714M250 610H352M250 675H352" />
  <path class="house-shell__door-fhole" d="M278 608c7-8 9-20 2-33c8 4 12 13 12 22c0 10-4 19-12 24c7 2 10 8 10 15c0 8-4 15-10 20c7 3 10 9 10 16c0 7-4 13-10 18" />
  <path class="house-shell__door-fhole" d="M324 608c-7-8-9-20-2-33c-8 4-12 13-12 22c0 10 4 19 12 24c-7 2-10 8-10 15c0 8 4 15 10 20c-7 3-10 9-10 16c0 7 4 13 10 18" />
  <circle class="house-shell__door-fhole-dot" cx="272" cy="593" r="3.5" />
  <circle class="house-shell__door-fhole-dot" cx="330" cy="593" r="3.5" />
  <circle class="house-shell__door-fhole-dot" cx="272" cy="662" r="3.5" />
  <circle class="house-shell__door-fhole-dot" cx="330" cy="662" r="3.5" />
  <path class="house-shell__door-threshold" d="M210 714H392V728H210Z" />

  <!-- More realistic entry steps -->
  <path class="house-shell__step-top" d="M196 728H406L397 736H205Z" />
  <path class="house-shell__step-face" d="M205 736H397V748H205Z" />
  <path class="house-shell__step-top" d="M179 748H423L414 757H188Z" />
  <path class="house-shell__step-face" d="M188 757H414V770H188Z" />
  <path class="house-shell__step-top" d="M160 770H442L431 780H171Z" />
  <path class="house-shell__step-face" d="M171 780H431V793H171Z" />
</g>
