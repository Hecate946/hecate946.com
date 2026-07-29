<script lang="ts">
  export let x = 0;
  export let y = 0;
  export let scale = 1;
  export let fill = '#101316';
  export let stroke = '#d5b978';
  export let strokeWidth = 1.5;
</script>

<g transform={`translate(${x} ${y}) scale(${scale})`} aria-hidden="true">
  <path
    d="M10 4H28V13H35V4H53V13H60V4H78V28L69 38V72L80 86V96H8V86L19 72V38L10 28Z"
    {fill}
    {stroke}
    stroke-width={strokeWidth}
    stroke-linejoin="round"
  />
  <path d="M19 28H69M19 39H69M19 72H69M12 86H76" fill="none" {stroke} stroke-width={strokeWidth} opacity="0.82" />
  <path d="M27 45H61V66H27Z" fill="#22282d" opacity="0.55" />
</g>
