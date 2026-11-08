(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x112 (= s_5 (_ bv127 8))))
(not $x112)))
(check-sat)
