(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1038 (= s_4 (_ bv1 4))))
(not $x1038)))
(check-sat)
