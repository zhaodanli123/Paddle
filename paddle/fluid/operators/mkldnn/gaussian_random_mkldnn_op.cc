/* Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

#include <string>
#include "paddle/fluid/framework/generator.h"
#include "paddle/fluid/operators/fill_constant_op.h"
#include "paddle/fluid/operators/mean_op.h"

namespace paddle {
namespace operators {

using framework::DataLayout;
template <typename T>
class GaussianMKLDNNKernel : public paddle::framework::OpKernel<T> {
 public:
  void Compute(const framework::ExecutionContext& context) const override {
    float mean = context.Attr<float>("mean");
    float std = context.Attr<float>("std");
    auto* tensor = context.Output<framework::Tensor>("Out");

    const std::string op_type = "gaussian_random";
    auto shape = GetShape(context, op_type);
    tensor->Resize(shape);
    T* data = tensor->mutable_data<T>(context.GetPlace());
    int64_t size = tensor->numel();
    std::normal_distribution<T> dist(mean, std);

    if (framework::Generator::GetInstance()->is_init_py) {
      std::mt19937_64& gen_engine =
          framework::Generator::GetInstance()->GetCPUEngine();
      for (int64_t i = 0; i < size; ++i) {
        data[i] = dist(gen_engine);
      }
    } else {
      unsigned int seed = static_cast<unsigned int>(context.Attr<int>("seed"));
      std::minstd_rand engine;
      if (seed == 0) {
        seed = std::random_device()();
      }
      engine.seed(seed);
      for (int64_t i = 0; i < size; ++i) {
        data[i] = dist(engine);
      }
    }

    tensor->set_layout(DataLayout::kMKLDNN);
    tensor->set_format(mkldnn::memory::format_tag::oihw);
  }
};
}  // namespace operators
}  // namespace paddle

namespace ops = paddle::operators;

REGISTER_OP_KERNEL(gaussian_random, MKLDNN, ::paddle::platform::CPUPlace,
                   ops::GaussianMKLDNNKernel<float>);
