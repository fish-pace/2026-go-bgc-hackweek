-- Turns the poster markup used in poster.qmd into Typst:
--   ::: {.block title="Methods"}     a titled box; add .highlight for an accent box
--   ::: {.colbreak}                   start the next column
--   ::: {#refs}                       where the bibliography goes
--   ![Caption](figures/x.png){script="scripts/x.py"}
--                                     adds a "Code:" link to the script in the caption

local code_base_url = ""
local bibliography = {}
local bibliography_style = nil

local function typst_escape(s)
  return (s:gsub("([%#%$%*_@<>%[%]\\`~])", "\\%1"))
end

local function get_meta(meta)
  if meta["code-base-url"] then
    code_base_url = pandoc.utils.stringify(meta["code-base-url"])
  end
  local bib = meta.bibliography
  if bib then
    if bib.t == "MetaList" or pandoc.utils.type(bib) == "List" then
      for _, b in ipairs(bib) do
        table.insert(bibliography, pandoc.utils.stringify(b))
      end
    else
      table.insert(bibliography, pandoc.utils.stringify(bib))
    end
  end
  if meta["bibliographystyle"] then
    bibliography_style = pandoc.utils.stringify(meta["bibliographystyle"])
  end
  -- A file path must reach Typst as written, without Markdown escaping (qr\_code.svg).
  if meta.qr then
    meta.qr = pandoc.MetaInlines({ pandoc.RawInline("typst", pandoc.utils.stringify(meta.qr)) })
  end
  return meta
end

local function bibliography_block()
  if #bibliography == 0 then
    return pandoc.Blocks({})
  end
  local files = {}
  for _, b in ipairs(bibliography) do
    table.insert(files, '"' .. b .. '"')
  end
  local args = "(" .. table.concat(files, ", ") .. ",), title: none"
  if bibliography_style then
    args = args .. ', style: "' .. bibliography_style .. '"'
  end
  return pandoc.Blocks({
    pandoc.RawBlock("typst", "#[\n#set text(size: 0.75em)\n#bibliography(" .. args .. ")\n]"),
  })
end

local function Div(div)
  if div.identifier == "refs" then
    return bibliography_block()
  end
  if div.classes:includes("colbreak") then
    return pandoc.RawBlock("typst", "#colbreak()")
  end
  if div.classes:includes("block") then
    local args = {}
    if div.attributes.title then
      table.insert(args, "title: [" .. typst_escape(div.attributes.title) .. "]")
    end
    if div.classes:includes("highlight") then
      table.insert(args, "highlight: true")
    end
    local blocks = pandoc.Blocks({
      pandoc.RawBlock("typst", "#poster-block(" .. table.concat(args, ", ") .. ")["),
    })
    blocks:extend(div.content)
    blocks:insert(pandoc.RawBlock("typst", "]"))
    return blocks
  end
end

local function Figure(fig)
  local script = nil
  fig.content:walk({
    Image = function(img)
      script = script or img.attributes.script
    end,
  })
  if not script then
    return nil
  end
  local link = pandoc.Link(script, code_base_url .. script)
  local caption = fig.caption.long
  local addition = { pandoc.Space(), pandoc.Str("Code:"), pandoc.Space(), link }
  if #caption > 0 and caption[#caption].content then
    caption[#caption].content:extend(addition)
  else
    caption:insert(pandoc.Plain(addition))
  end
  fig.caption.long = caption
  return fig
end

return {
  { Meta = get_meta },
  { Div = Div, Figure = Figure },
}
