// Maps the YAML header of poster.qmd onto the arguments of `poster()`
// in typst-template.typ.
#show: doc => poster(
$if(title)$
  title: [$title$],
$endif$
$if(by-author)$
  authors: (
$for(by-author)$
    (
      name: [$it.name.literal$],
      affiliations: ($for(it.affiliations)$"$it.id$",$endfor$),
    ),
$endfor$
  ),
$endif$
$if(by-affiliation)$
  affiliations: (
$for(by-affiliation)$
    (id: "$it.id$", name: [$it.name$]),
$endfor$
  ),
$endif$
$if(qr)$
  qr: "$qr$",
$endif$
$if(qr-caption)$
  qr-caption: [$qr-caption$],
$endif$
$if(poster-footer)$
  footer: [$poster-footer$],
$endif$
$if(poster-columns)$
  ncols: $poster-columns$,
$endif$
$if(poster-width)$
  width: $poster-width$,
$endif$
$if(poster-height)$
  height: $poster-height$,
$endif$
$if(fontsize)$
  fontsize: $fontsize$,
$endif$
  doc,
)
