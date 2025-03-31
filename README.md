# 🕵️ CrimeWatch
<div align="center">
  <img src="./readme/crimewatch.jpg"></img>
</div>
CrimeWatch is a tool that produces a heatmap of criminal cases with reported judgments as found on eLitigation. It scrapes data from the site using BeautifulSoup and processes it for analysis.

## 🚧 Status

CrimeWatch is currently in development.
- ✅ Web scraper is built
- ❌ Heatmap feature is deprecated and not functional yet

## 📥 Installation

To run CrimeWatch, install the required dependencies:

```bash
pip install pandas requests beautifulsoup4 ftfy spacy
```

and run:
```bash
python crimewatcher.py
```

## 🔍 Data Retrieval

The scraper currently retrieves the following fields:
- 🆔 **CaseIdentifier**
- ⚖️ **Charges**
- 📍 **Locations**
- 🔑 **Offence Category**
- 📅 **Year**
- 🔗 **URL**

## 🚀 Usage

Once installed, you can run the scraper to fetch case data. The heatmap visualization is not yet available.

## 🤝 Contributing

CrimeWatch is a work in progress. Contributions are welcome, especially for improving data visualization and refining scraped data.

## 📜 License

This project is open-source under the [MIT License](LICENSE).
