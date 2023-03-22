require "uri"
require "file_utils"
require "spoved/system_cmd"
require "./helper"

@[Spoved::Cli::Command(name: :update, descr: "update card data")]
class Mtg::Models::Cli::Update
  spoved_logger
  include Spoved::SystemCmd
  include Mtg::Models::Helper

  @temp_dir = File.expand_path("./tmp")

  def run(cmd, options, arguments)
    FileUtils.mkdir_p(@temp_dir) unless Dir.exists?(@temp_dir)
    __update_scryfall_data(@temp_dir)
  end

  private def __update_scryfall_data(dir)
    logger.info { "fetching all cards" }
    self.scryfall_all_cards(dir)
    logger.info { "done" }
  end
end
