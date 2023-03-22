module Mtg::Models::Helper
  # Use existing file if present, otherwise download from scryfall. Will return path to the data file.
  def fetch_scryfall_data_local_file(uri, dir) : String
    filename = File.basename(uri.to_s)
    file_path = File.join(dir, filename)
    if File.exists?(file_path)
      logger.info { "using local file #{file_path}" }
    else
      logger.info { "downloading #{filename}" }
      File.open(file_path, "w") do |file|
        HTTP::Client.get(uri) do |response|
          response.status_code # => 200
          IO.copy(response.body_io, file)
        end
      end
      logger.info { "finished downloading #{filename}" }
    end
    file_path
  end

  def scryfall_bulk
    bulk_data = Scryfall::Api.bulk_data
    bulk = bulk_data.find { |b| b.bulk_type == "all_cards" }
    raise "no bulk data found" if bulk.nil?
    bulk
  end

  def scryfall_all_cards(dir = "./tmp")
    bulk = self.scryfall_bulk
    file_path = self.fetch_scryfall_data_local_file(bulk.download_uri, dir)
    logger.info { "parsing #{file_path}" }
    data = Array(Scryfall::Card).from_json(File.read(file_path))
    raise "unable to fetch data" if data.nil?
    data
  end
end
