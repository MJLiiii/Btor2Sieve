(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x6869 (= i_4 (_ bv0 32))))
(not $x6869)))
(check-sat)
