const path = require("path");

module.exports = {
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  optimization: {
    splitChunks: {
      chunks: "all",
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: "vendors",
          chunks: "all",
        },
        aws: {
          test: /[\\/]node_modules[\\/](@aws-sdk|aws-amplify)[\\/]/,
          name: "aws",
          chunks: "all",
        },
        ui: {
          test: /[\\/]node_modules[\\/](@chakra-ui|@emotion)[\\/]/,
          name: "ui",
          chunks: "all",
        },
      },
    },
  },
};
