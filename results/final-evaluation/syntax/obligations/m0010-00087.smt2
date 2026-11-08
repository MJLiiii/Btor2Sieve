(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x6194 (= i_4 (_ bv2147483647 32))))
(not $x6194)))
(check-sat)
