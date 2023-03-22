require "spoved/cli"
require "spoved/cli/arg_macros"
require "scryfall"

class Mtg::Models::Cli::Main < Spoved::Cli::Main
  SHORT_DESC = "mtg-models"
  LONG_DESC  = "MTG Models CLI : #{Mtg::Models::VERSION}"

  def config(cmd : Commander::Command)
    cmd.use = SHORT_DESC
    cmd.long = LONG_DESC
  end
end

require "./*"
