(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 (let (($x20 (and (= (_ bv0 8) s_5))))
 (and $x20 true)))
(assert
 (let (($x107 (bvule s_5 (_ bv128 8))))
(not $x107)))
(check-sat)
