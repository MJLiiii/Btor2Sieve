(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x272 (= i_7 (_ bv127 8))))
(not $x272)))
(check-sat)
