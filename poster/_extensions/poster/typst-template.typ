// Poster layout. Quarto passes the YAML header of poster.qmd to `poster()`
// through typst-show.typ. Sizes and colors are set here.

#let poster-primary = rgb("#1f3b57")
#let poster-accent = rgb("#2a9d8f")
#let poster-background = rgb("#eef3f6")

// A titled box. poster.lua turns `::: {.block title="..."}` into a call to this;
// add `.highlight` to the div for an accent-colored box.
#let poster-block(title: none, highlight: false, body) = block(
  width: 100%,
  breakable: false,
  fill: if highlight { poster-accent.lighten(88%) } else { white },
  stroke: if highlight { 4pt + poster-accent } else { none },
  radius: 14pt,
  inset: (x: 0.5in, y: 0.45in),
  below: 0.6in,
)[
  #if title != none {
    block(below: 0.3in)[
      #text(size: 1.5em, weight: "bold", fill: poster-primary, title)
      #v(-0.15in)
      #line(length: 100%, stroke: 4pt + poster-accent)
    ]
  }
  #body
]

#let poster(
  title: none,
  authors: (),
  affiliations: (),
  qr: none,
  qr-caption: none,
  footer: none,
  ncols: 3,
  width: 42in,
  height: 42in,
  font: ("Roboto", "Nimbus Sans", "TeX Gyre Heros", "Libertinus Serif"),
  fontsize: 32pt,
  doc,
) = {
  set page(
    width: width,
    height: height,
    margin: (x: 1in, top: 0.8in, bottom: 1.2in),
    fill: poster-background,
    numbering: none,
    footer: if footer != none {
      set text(size: 0.75em, fill: poster-primary)
      line(length: 100%, stroke: 2pt + poster-primary)
      v(-0.1in)
      footer
    },
  )
  set text(font: font, size: fontsize, stretch: 100%)
  set par(leading: 0.6em, spacing: 0.9em)
  set list(indent: 0.3em)
  show heading: set text(fill: poster-primary)
  show heading: set block(above: 0.8em, below: 0.4em)
  show figure.caption: set text(size: 0.8em)
  show link: set text(fill: poster-accent.darken(20%))

  // Affiliations are numbered in the order they are listed in the YAML.
  let affil-number(id) = {
    let i = affiliations.position(a => a.id == id)
    if i == none { "?" } else { str(i + 1) }
  }
  let author-line = authors
    .map(a => [#a.name#super(a.affiliations.map(affil-number).join(","))])
    .join(", ")
  let affil-line = affiliations
    .enumerate()
    .map(((i, a)) => [#super(str(i + 1))#a.name])
    .join([#h(1em)])

  block(
    width: 100%,
    fill: poster-primary,
    radius: 14pt,
    inset: 0.6in,
    below: 0.7in,
  )[
    #set text(fill: white)
    #grid(
      columns: (1fr, auto),
      column-gutter: 0.8in,
      align: (left + horizon, center + horizon),
      [
        #text(size: 3.2em, weight: "bold", title)
        #v(0.2in)
        #text(size: 1.5em, author-line)
        #v(0.05in)
        #text(size: 1.1em, affil-line)
      ],
      if qr != none {
        box(fill: white, inset: 0.15in, radius: 8pt, image(qr, width: 5in))
        if qr-caption != none { block(above: 0.15in, text(size: 0.8em, qr-caption)) }
      },
    )
  ]

  columns(ncols, gutter: 0.7in, doc)
}
